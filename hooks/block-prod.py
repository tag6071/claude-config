#!/usr/bin/python3
"""
PreToolUse hook: hard-block Bash commands that look like they target production.

Reads JSON from stdin (Claude Code hook protocol). Exits:
  0 -> allow
  2 -> block (stderr shown to Claude, command is refused)

Generic patterns are hardcoded below. Project-specific identifiers (hostnames,
DB names, account/project IDs, etc.) live in ~/.claude/prod-patterns.txt, one
regex per line. Blank lines and lines starting with '#' are ignored.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Ensure the hooks dir is importable no matter how we're loaded (standalone,
# or via importlib from a foreign sys.path in the dispatcher). A failed import
# here would make the dispatcher SILENTLY SKIP this security guard.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import elide_prose

PATTERNS_FILE = Path.home() / ".claude" / "prod-patterns.txt"
BYPASS_ENV = "CLAUDE_ALLOW_PROD"  # user can set this in their own shell to override

# Generic patterns (no project-specific identifiers needed).
# Each entry: (label, regex). Regex is matched case-insensitively against the full command.
GENERIC_PATTERNS: list[tuple[str, str]] = [
    # Explicit prod flags / env vars
    ("--prod / --production flag", r"(?<![\w-])--prod(uction)?\b"),
    ("NODE_ENV=production", r"\bNODE_ENV\s*=\s*[\"']?production\b"),
    ("RAILS_ENV=production", r"\bRAILS_ENV\s*=\s*[\"']?production\b"),
    ("APP_ENV=prod", r"\bAPP_ENV\s*=\s*[\"']?prod(uction)?\b"),
    ("ENVIRONMENT=prod", r"\bENVIRONMENT\s*=\s*[\"']?prod(uction)?\b"),
    ("FLASK_ENV=production", r"\bFLASK_ENV\s*=\s*[\"']?production\b"),
    ("DJANGO_SETTINGS prod", r"\bDJANGO_SETTINGS_MODULE\s*=\s*\S*prod"),

    # Hostname / URL shapes that look prod
    ("prod-* hostname/url", r"\bprod[-.][a-z0-9][\w.-]*"),
    ("*-prod hostname/url", r"[\w.-]+[-.]prod\b"),
    ("production-* hostname/url", r"\bproduction[-.][a-z0-9][\w.-]*"),
    ("*.production. host", r"[\w.-]+\.production\."),

    # Destructive SQL (run via psql/mysql/sqlite3/etc.)
    ("DROP DATABASE/TABLE/SCHEMA", r"\bDROP\s+(DATABASE|TABLE|SCHEMA|USER|ROLE)\b"),
    # SQL shape only: "TRUNCATE TABLE x" or "TRUNCATE x;" (or CASCADE/RESTART/end of line). The Tailwind
    # class "truncate border-2 ..." matched the old "TRUNCATE <word>" and blocked UI work.
    ("TRUNCATE", r"(?m)\bTRUNCATE\s+(TABLE\b|(ONLY\s+)?[\"\w.]+\s*(;|$|\bCASCADE\b|\bRESTART\b))"),
    ("DELETE FROM without WHERE", r"\bDELETE\s+FROM\s+\w[\w.\"]*\s*(;|$|--|\|)"),
    ("UPDATE without WHERE", r"\bUPDATE\s+\w[\w.\"]*\s+SET\s+[^;]*?(?<!\bWHERE)\s*(;|$)"),

    # Destructive shell
    ("rm -rf /", r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+/(?!tmp|var/tmp|private/tmp)"),
    ("fork bomb", r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:"),
    ("dd to /dev/disk", r"\bdd\b.*\bof=/dev/(disk|sd|nvme|rdisk)"),
    ("mkfs", r"\bmkfs(\.\w+)?\b"),

    # Destructive git on shared branches
    ("git push --force to main/master", r"git\s+push\s+(--force\b|-f\b|--force-with-lease\b)[^\n]*\b(main|master|prod|production|release)\b"),
    ("git push --force (any)", r"git\s+push\s+(--force(?!-with-lease)\b|-f\b)"),
    ("git reset --hard origin", r"git\s+reset\s+--hard\s+origin"),
    ("git branch -D main/master", r"git\s+branch\s+-D\s+(main|master|prod|production)\b"),

    # Infrastructure-as-code, container, cloud destructive
    ("terraform apply/destroy", r"\bterraform\s+(apply|destroy)\b"),
    ("pulumi up/destroy", r"\bpulumi\s+(up|destroy)\b"),
    ("kubectl delete", r"\bkubectl\s+(delete|drain|cordon)\b"),
    ("kubectl prod context", r"\bkubectl\s+[^\n]*--context[\s=]\S*prod"),
    ("helm uninstall/delete", r"\bhelm\s+(uninstall|delete)\b"),
    ("docker system prune -a", r"\bdocker\s+system\s+prune\s+.*-a"),

    # AWS / GCP / Azure destructive or prod-targeted
    ("aws --profile prod", r"\baws\s+[^\n]*--profile[\s=]\S*prod"),
    ("aws s3 rb / rm --recursive", r"\baws\s+s3\s+(rb\b|rm\s+[^\n]*--recursive)"),
    ("aws rds delete-*", r"\baws\s+rds\s+delete-"),
    ("aws ec2 terminate-instances", r"\baws\s+ec2\s+terminate-instances\b"),
    ("aws dynamodb delete-table", r"\baws\s+dynamodb\s+delete-table\b"),
    ("gcloud prod project", r"\bgcloud\s+[^\n]*--project[\s=]\S*prod"),
    ("gcloud sql instances delete", r"\bgcloud\s+sql\s+instances\s+delete\b"),
    ("az ... prod subscription/group", r"\baz\s+[^\n]*--(subscription|resource-group)[\s=]\S*prod"),

    # Database CLIs pointed at prod-looking URIs
    ("postgres prod URI", r"postgres(ql)?://[^\s\"']*prod"),
    ("mysql prod URI", r"mysql://[^\s\"']*prod"),
    ("mongodb prod URI", r"mongodb(\+srv)?://[^\s\"']*prod"),
    ("redis prod URI", r"rediss?://[^\s\"']*prod"),

    # Reading prod credential files
    ("read .env.prod*", r"(?<![\w/.])\.env\.prod(uction)?\b"),
    ("read prod credentials file", r"(?<![\w/.])(credentials|secrets|tokens)\.prod(uction)?\b"),
]


def load_user_patterns() -> list[tuple[str, str]]:
    if not PATTERNS_FILE.exists():
        return []
    out: list[tuple[str, str]] = []
    for raw in PATTERNS_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.append((f"user pattern: {line}", line))
    return out


def scan(command: str) -> list[str]:
    """Return list of human-readable match labels (empty = allowed)."""
    hits: list[str] = []
    for label, pat in GENERIC_PATTERNS + load_user_patterns():
        try:
            if re.search(pat, command, flags=re.IGNORECASE | re.DOTALL):
                hits.append(label)
        except re.error:
            # Bad user-supplied regex: surface it loudly, don't crash silently.
            hits.append(f"INVALID regex in prod-patterns.txt: {pat}")
    return hits


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        # If we can't parse the hook payload, fail open (don't break the harness).
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0

    # Strip references to this hook system's own files before scanning so
    # routine maintenance (cat/cp/rsync of the hook itself or its patterns
    # file) doesn't self-trigger the very rules it defines.
    self_ref_re = re.compile(r"\b(prod-patterns(?:\.txt)?|block-prod(?:\.py)?)\b")
    command_for_scan = self_ref_re.sub("HOOKFILE", command)

    # PROSE THAT MENTIONS a destructive verb is not the verb: a commit message
    # containing "un-truncate" matched TRUNCATE and blocked its own commit.
    command_for_scan = elide_prose(command_for_scan)

    hits = scan(command_for_scan)
    if not hits:
        return 0

    bullets = "\n".join(f"  • {h}" for h in hits)
    sys.stderr.write(
        "BLOCKED by ~/.claude/hooks/block-prod.py — this command matched "
        "production-isolation patterns:\n"
        f"{bullets}\n\n"
        "Per ~/.claude/CLAUDE.md (Production isolation): tests, scripts, and dev "
        "work never touch production. STOP and surface this to the user. If they "
        "confirm prod access is genuinely required, THEY run the command — not you.\n\n"
        f"Patterns file: {PATTERNS_FILE}\n"
        f"Emergency bypass (user-set, single shell only): export {BYPASS_ENV}=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
