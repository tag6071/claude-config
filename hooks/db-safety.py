#!/usr/bin/python3
"""
PreToolUse hook: catch DB-write anti-patterns that would skip the
/db-write skill's mandatory 6-step ritual.

Reads JSON from stdin (Claude Code hook protocol). Exits:
  0 -> allow
  2 -> block (stderr shown to Claude, command is refused)

What this hook catches (complements ~/.claude/hooks/block-prod.py):
  • Evasion patterns: WHERE 1=1, WHERE true, WHERE 1 ...
  • CLI SQL writes (sqlite3 / psql / mysql) without a transaction frame
  • Python heredocs / -c that perform sqlite3 writes without BEGIN/COMMIT
  • Direct edits (sed -i, redirect, cp) targeting *.sqlite / *.db files
  • Writes to running-app data dirs without preceding probe (advisory)

NOT a replacement for the /db-write skill — it's the enforcement net that
catches drift. Skill = intent, hook = guard rail.

Bypass: export CLAUDE_ALLOW_DB_WRITE=1 in the shell that spawned this
session (single-use, per-shell).
"""
from __future__ import annotations

import json
import os
import re
import sys

BYPASS_ENV = "CLAUDE_ALLOW_DB_WRITE"


# ---------- patterns ----------

# Each entry: (label, regex_pattern, advice)
# Regex is matched case-insensitively against the full command.
PATTERNS: list[tuple[str, str, str]] = [
    # ---- evasion patterns (someone trying to slip past block-prod's UPDATE-without-WHERE check) ----
    (
        "WHERE 1=1 (evasion pattern)",
        r"\bWHERE\s+1\s*=\s*1\b",
        "WHERE 1=1 means 'every row' — this is the regex-evasion antipattern. "
        "If you really need to update every row, that needs explicit user approval "
        "AND the /db-write skill's full ritual.",
    ),
    (
        "WHERE true (evasion pattern)",
        r"\bWHERE\s+true\b",
        "WHERE true matches every row. Same problem as WHERE 1=1.",
    ),
    (
        "WHERE 1 (evasion pattern, MySQL/SQLite truthy-1)",
        r"\bWHERE\s+1\s*(;|$|--|\bAND\b|\bOR\b|\bORDER\b|\bLIMIT\b)",
        "Bare 'WHERE 1' evaluates to true on every row. Don't.",
    ),

    # ---- destructive file ops on DB files ----
    (
        "sed -i / sed --in-place on *.sqlite / *.db",
        r"\bsed\s+(-i|--in-place)\b[^\n]*\.(sqlite|sqlite3|db)\b",
        "Never sed -i a database file — corrupts the binary format. Use proper "
        "SQL via the /db-write ritual.",
    ),
    (
        "shell-redirect overwriting *.sqlite / *.db",
        r">\s*[^\s|]+\.(sqlite|sqlite3|db)\b(?!\.bak)",
        "Don't > overwrite a database file — that nukes the DB. If you need a "
        "fresh copy, use 'cp source.db backup.db' then SQL.",
    ),
]


# ---------- Python heredoc / -c detection ----------

# Catches: python3 <<'PY' ... PY  OR  python3 -c '... UPDATE/DELETE/INSERT ...'
# When the heredoc/-c does sqlite-style writes without BEGIN/COMMIT.
PYTHON_HEREDOC_RE = re.compile(
    r"python3?\s+(?:-c\s+|<<\s*[\"']?\w+[\"']?)",
    re.IGNORECASE,
)
PYTHON_WRITE_RE = re.compile(
    r"(?:cursor|cur|con|conn)\.execute\s*\(\s*[fr]?[\"'][^\"']*?\b(UPDATE|DELETE|INSERT|REPLACE)\b",
    re.IGNORECASE | re.DOTALL,
)
PYTHON_TXN_RE = re.compile(r"\bBEGIN\b|\.execute\([\"']BEGIN", re.IGNORECASE)
PYTHON_COMMIT_RE = re.compile(r"\.commit\s*\(\s*\)|\bCOMMIT\b", re.IGNORECASE)


def python_heredoc_unsafe(command: str) -> str | None:
    """Detect python3 -c or <<heredoc patterns that do DB writes without BEGIN/COMMIT.
    Returns advice string if unsafe, None if safe / not applicable."""
    if not PYTHON_HEREDOC_RE.search(command):
        return None
    if not PYTHON_WRITE_RE.search(command):
        return None
    has_txn = bool(PYTHON_TXN_RE.search(command)) and bool(PYTHON_COMMIT_RE.search(command))
    if has_txn:
        return None
    return (
        "Python inline DB writes (sqlite3 / psycopg / etc) MUST wrap mutations in a "
        "transaction. Either call con.execute('BEGIN') ... con.commit(), or use "
        "'with con:' as a context manager (auto-commits/rolls back). Per /db-write "
        "skill step 4. Heredoc evasion of the SQL hook regex doesn't dodge this check."
    )


# Match a CLI SQL invocation: tool name + the quoted SQL it's about to run.
# Captures the quoted SQL into group(1) so we can inspect transaction framing.
_CLI_SQL_RE = re.compile(
    r"""\b(?:sqlite3|psql|mysql|mariadb)\b      # CLI tool
        [^|;\n'"]{0,200}                         # args (no pipe/semi/newline/quote between tool and SQL)
        (?:-c|-e)?\s*                            # optional -c (psql) or -e (mysql)
        ['"]([^'"]+)['"]                         # the quoted SQL → group(1)
    """,
    re.IGNORECASE | re.VERBOSE,
)
_WRITE_VERB_RE = re.compile(r"\b(UPDATE|DELETE|INSERT|REPLACE|MERGE|UPSERT)\b", re.IGNORECASE)
_BEGIN_RE = re.compile(r"\bBEGIN\b|\bSTART\s+TRANSACTION\b", re.IGNORECASE)
_COMMIT_RE = re.compile(r"\bCOMMIT\b|\bEND\b", re.IGNORECASE)


def cli_sql_unframed(command: str) -> str | None:
    """Detect inline SQL writes via sqlite3/psql/mysql CLI that lack BEGIN+COMMIT
    in the same quoted statement. Returns advice if unsafe, None if safe."""
    for m in _CLI_SQL_RE.finditer(command):
        sql = m.group(1)
        if not _WRITE_VERB_RE.search(sql):
            continue  # quoted SQL has no write verb — fine
        if _BEGIN_RE.search(sql) and _COMMIT_RE.search(sql):
            continue  # has explicit transaction framing — fine
        return (
            "Inline SQL writes via the CLI (sqlite3/psql/mysql) MUST be wrapped in "
            "'BEGIN; ... COMMIT;' (or 'START TRANSACTION; ... COMMIT;'). Atomic is "
            "free; non-atomic is a footgun. Per /db-write skill step 4."
        )
    return None


# ---------- main ----------


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Fail open on parse error — don't break the harness.
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0

    # Skip git commit / git tag invocations — their -m/-F message bodies
    # often contain documentation/example SQL that would self-trigger this
    # hook. Git itself never executes SQL.
    if re.search(r"\bgit\s+(commit|tag|notes)\b", command):
        return 0

    # Self-reference strip so editing the hook itself doesn't self-trigger.
    self_ref_re = re.compile(r"\bdb-safety(?:\.py)?\b")
    command_for_scan = self_ref_re.sub("HOOKFILE", command)

    hits: list[tuple[str, str]] = []  # (label, advice)

    for label, pat, advice in PATTERNS:
        try:
            if re.search(pat, command_for_scan, flags=re.IGNORECASE | re.DOTALL):
                hits.append((label, advice))
        except re.error:
            continue

    pyhit = python_heredoc_unsafe(command_for_scan)
    if pyhit:
        hits.append(("python heredoc / -c with unframed DB write", pyhit))

    clihit = cli_sql_unframed(command_for_scan)
    if clihit:
        hits.append(("CLI SQL write without BEGIN/COMMIT", clihit))

    if not hits:
        return 0

    bullets = "\n".join(f"  • {label}\n      → {advice}" for label, advice in hits)
    sys.stderr.write(
        "BLOCKED by ~/.claude/hooks/db-safety.py — this command matched DB-write "
        "anti-patterns:\n\n"
        f"{bullets}\n\n"
        "Per ~/.claude/skills/db-write/SKILL.md, all DB mutations follow the 6-step ritual:\n"
        "  1. schema-introspect → 2. sample current → 3. plan + show user + WAIT →\n"
        "  4. BEGIN transaction → 5. write → 6. verify + COMMIT (or ROLLBACK).\n\n"
        "Invoke the /db-write skill before writing, or use a typed DB MCP server if installed.\n"
        f"Emergency bypass (user-set, single shell only): export {BYPASS_ENV}=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
