#!/usr/bin/python3
"""
PreToolUse hook: hard-block tool calls that touch secrets, credentials, or private keys.

Runs on Bash AND Read tool calls. Reads JSON from stdin (Claude Code hook protocol).
  Bash → scans tool_input.command
  Read → scans tool_input.file_path

Exits:
  0 -> allow
  2 -> block (stderr shown to Claude, the call is refused)

Generic patterns hardcoded below. Project-specific paths (custom secret files,
unusual credential dirs) live in ~/.claude/secret-patterns.txt, one regex per
line. Blank lines and lines starting with '#' are ignored.

Sibling to block-prod.py — independent concern, independent file. Disable each
separately from settings.json if needed.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# See block-prod.py: guarantee hook_common resolves however we're loaded, so a
# path quirk can never silently disable this guard.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import elide_prose

PATTERNS_FILE = Path.home() / ".claude" / "secret-patterns.txt"
BYPASS_ENV = "CLAUDE_ALLOW_SECRETS"  # user-set in their own shell to override

# Each entry: (label, regex). Matched case-insensitively.
GENERIC_PATTERNS: list[tuple[str, str]] = [
    # SSH private keys (id_rsa, id_ed25519, id_ecdsa, id_dsa) — .pub variants allowed.
    ("SSH private key (id_*)", r"\bid_(?:rsa|ed25519|ecdsa|dsa)(?!\.pub)\b"),

    # Private key / certificate file extensions
    ("private key (*.pem)", r"\.pem\b"),
    ("private key (*.key)", r"\.key\b"),
    ("PKCS#12 keystore (*.p12/*.pfx)", r"\.(?:p12|pfx)\b"),
    ("Java keystore (*.jks)", r"\.jks\b"),

    # Standard credential stores
    ("AWS credentials file", r"\.aws/credentials\b"),
    ("AWS config (may hold SSO sessions)", r"\.aws/config\b"),
    ("GnuPG store", r"\.gnupg/"),
    # Blocks reading FILES under .ssh/ — not the directory itself (mkdir/ls/install -d
    # are benign). *.pub is a PUBLIC key, allowlisted with the other non-secret files.
    (
        "SSH private dir",
        r"\.ssh/(?!known_hosts\b|config\b|authorized_keys\b|[^\s/'\"]*\.pub\b)[^\s/'\"]",
    ),
    ("npm auth (.npmrc)", r"\.npmrc\b"),
    ("pip auth (.pypirc)", r"\.pypirc\b"),
    ("netrc auth", r"\.netrc\b"),
    ("kubeconfig", r"(?<!\w)kubeconfig\b"),
    ("gcloud creds dir", r"\.config/gcloud/"),
    ("Azure CLI creds", r"\.azure/(?:accessTokens|azureProfile)"),
    ("Docker config", r"\.docker/config\.json\b"),

    # System credential files
    ("/etc/shadow", r"/etc/shadow\b"),
    ("/etc/sudoers", r"/etc/sudoers\b"),

    # .env files (allow .env.example, .env.sample, .env.template, .env.dist, .envrc)
    (".env file (non-example)", r"(?<![\w.])\.env(?!\.example|\.sample|\.template|\.dist|rc\b)(?:\.[a-zA-Z0-9_-]+)?\b"),

    # Common secret/credential/password/token CONFIG FILE shapes
    # (allow secrets.yml.example/.sample/.template/.dist — placeholder templates, no real secret)
    ("secrets.* config file", r"(?<![\w.-])secrets?\.(?:ya?ml|json|txt|env|cfg|conf|ini|toml|sh|js|ts|py)(?!\.example|\.sample|\.template|\.dist)\b"),
    ("credentials.* config file", r"(?<![\w.-])credentials?\.(?:ya?ml|json|txt|env|cfg|conf|ini|toml|sh|js|ts|py)\b"),
    ("passwords.* file", r"(?<![\w.-])passwords?\.(?:txt|csv|ya?ml|json|kdbx|gpg)\b"),
    ("tokens.* file", r"(?<![\w.-])tokens?\.(?:txt|json|ya?ml)\b"),
    ("api[-_]key file", r"\bapi[-_]?keys?\.(?:txt|json|ya?ml|env)\b"),

    # Inline auth in command args (curl, headers)
    ("inline Bearer token", r"\bBearer\s+[A-Za-z0-9._\-+/=]{8,}"),
    ("inline Authorization header", r"Authorization:\s*\S"),
    ("X-API-Key header", r"X-Api-Key:\s*\S"),
    ("curl -u user:password", r"\bcurl\s+[^|\n;]*\s-u\s+\S+:\S"),

    # Database URIs with embedded credentials
    ("postgres URI with credentials", r"postgres(?:ql)?://[^:/\s]+:[^@/\s]+@"),
    ("mysql URI with credentials", r"mysql://[^:/\s]+:[^@/\s]+@"),
    ("mongodb URI with credentials", r"mongodb(?:\+srv)?://[^:/\s]+:[^@/\s]+@"),
    ("redis URI with credentials", r"rediss?://[^:/\s]*:[^@/\s]+@"),

    # CLI password leaks
    ("mysql -p<password>", r"\bmysql\s+[^|\n;]*-p[A-Za-z0-9]"),
    ("PGPASSWORD inline", r"\bPGPASSWORD\s*=\s*[\"']?\S"),

    # git-crypt key operations (exposes plaintext or exports the symmetric key)
    ("git-crypt unlock/export-key", r"\bgit-crypt\s+(?:unlock|export-key)\b"),

    # ssh-keygen exporting a private key
    ("ssh-keygen private-key export", r"\bssh-keygen\s+[^|\n;]*-e\b"),
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


# ---------------------------------------------------------------------------
# Content sniff.
#
# Filename lists always lose. A config file held an RSA private key and matched
# nothing above; a `sed -n 1,60p` on it dumped the key into a transcript. The
# file's CONTENT is the invariant, not its name.
#
# Layering: sniffing needs a LOCAL file, so `ssh host "cat /etc/x"` can't be
# sniffed. The name patterns above remain the outer layer.
# ---------------------------------------------------------------------------

# NB: this file necessarily contains the PEM literal below, and test_block_secrets.py
# necessarily contains a fake key body. Sniffing either would brick the hook, hence
# SNIFF_EXEMPT_DIRS.
_PEM = re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")
_VAULT = re.compile(r"^\$ANSIBLE_VAULT;", re.MULTILINE)
_CRED = re.compile(r"\$(?:plaintext|pbkdf2-sha512|argon2id)\$")
_ASSIGN = re.compile(
    r"(?im)^\s*[-\w.]*"
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|passphrase|client[_-]?secret)"
    r"\s*[:=]\s*"
    r"(?!.*(\{\{|\$\{|<|CHANGEME|REPLACE|xxx|example|placeholder|null|~\s*$|\"\"|''))"
    r"(?P<value>\S{8,})"
)

# A "secret assignment" whose VALUE is CODE, not a literal: `TOKEN = os.environ[...]`,
# `notifyToken=NOTIFY_TOKEN,`, `api_key=self.key`. Source that merely PASSES a secret
# around holds no secret, and flagging it locks the file against READING *and* EDITING.
# Caught in practice: a provisioning script (one env-derived token + two kwarg
# references, zero literals) was unreadable and unpatchable.
_CODEREF = re.compile(
    r"^(?:"
    r"os\.environ|os\.getenv|getenv\(|process\.env|Deno\.env|System\.getenv|ENV\[|"
    r"secrets\.token|getpass|input\("            # env / derived getters
    r"|\$\(|`"                                   # shell command substitution: KEY=$(…)
    r"|(?:self|args|opts|config|cfg|conf|params|kwargs|env)\.\w"  # attribute reads
    # bare identifier in kwarg/call position — must carry an `_` or a capital, so a
    # lowercase literal like `password: hunter2hunter,` still counts as a secret.
    r"|[A-Za-z0-9]*[A-Z_][A-Za-z0-9_]*\s*[,)]"
    r")"
)


def _assign_hits(text: str) -> int:
    """Count secret assignments, skipping ones whose VALUE is a code reference."""
    return sum(
        1 for m in _ASSIGN.finditer(text) if not _CODEREF.match(m.group("value"))
    )

SNIFF_EXEMPT_DIRS = (Path(__file__).resolve().parent,)  # this hook's own dir, wherever installed
SKIP_DIR_PARTS = {
    "node_modules", ".venv", "venv", "dist", "build", "target",
    ".next", "__pycache__", ".git",
}
MAX_FILE_BYTES = 2_000_000
SNIFF_BYTES = 64 * 1024
MAX_CANDIDATES = 3

# Cheap gate: if no token looks like a path, do zero extra work. bash-guard.py
# exists to kill per-call overhead; a stat/fork on every `git status` would undo it.
_PATHISH = re.compile(r"[/\\]|\.\w{1,6}\b")


def sniff_secret(text: str) -> list[str]:
    """All secret signals present in `text` (does not decide block/allow)."""
    hits: list[str] = []
    if _PEM.search(text):
        hits.append("PEM private key block")
    if _VAULT.search(text):
        hits.append("ansible-vault encrypted payload")
    if _CRED.search(text):
        hits.append("credential hash marker ($plaintext$/$pbkdf2$/$argon2id$)")
    n = _assign_hits(text)
    if n:
        hits.append(f"{n} non-placeholder secret assignment(s)")
    return hits


def sniff_blocks(text: str, git_ignored: bool = False) -> list[str]:
    """Labels if this content must be blocked, else []."""
    strong = []
    if _PEM.search(text):
        strong.append("PEM private key block")
    if _VAULT.search(text):
        strong.append("ansible-vault encrypted payload")
    if _CRED.search(text):
        strong.append("credential hash marker")
    n = _assign_hits(text)
    if strong:
        return strong + ([f"{n} secret assignment(s)"] if n else [])
    if n >= 2:
        return [f"{n} non-placeholder secret assignments"]
    if n == 1 and git_ignored:
        return ["1 secret assignment in a git-ignored file"]
    return []


def is_git_ignored(path: Path) -> bool:
    """`git check-ignore -q` → 0 ignored, 1 not, 128 outside a repo. Any non-zero = not."""
    import subprocess

    try:
        return (
            subprocess.run(
                ["git", "-C", str(path.parent), "check-ignore", "-q", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            ).returncode
            == 0
        )
    except Exception:
        return False


def _exempt(p: Path) -> bool:
    if any(part in SKIP_DIR_PARTS for part in p.parts):
        return True
    return any(str(p).startswith(str(d)) for d in SNIFF_EXEMPT_DIRS)


def candidate_paths(cmd: str, cwd: Path) -> list[Path]:
    """Local, small, non-vendor files named by this command."""
    if not _PATHISH.search(cmd):
        return []
    import shlex

    try:
        toks = shlex.split(cmd)
    except ValueError:
        # Unbalanced quotes — guaranteed in nested-quote ssh one-liners.
        toks = cmd.split()

    out: list[Path] = []
    for tok in toks:
        if tok.startswith("-") or not _PATHISH.search(tok):
            continue
        try:
            p = Path(tok)
            p = p if p.is_absolute() else cwd / p
            if not p.is_file() or _exempt(p):
                continue
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except Exception:
            continue
        out.append(p)
        if len(out) >= MAX_CANDIDATES:
            break
    return out


def sniff_path(p: Path) -> list[str]:
    """Block labels for a single local file, or []."""
    if _exempt(p):
        return []
    try:
        if not p.is_file() or p.stat().st_size > MAX_FILE_BYTES:
            return []
        text = p.read_text(errors="ignore")[:SNIFF_BYTES]
    except Exception:
        return []
    # git check-ignore forks a subprocess: only ever as a BOOSTER, never on the
    # common path. Cheap signals must fail first.
    quick = sniff_blocks(text, git_ignored=False)
    if quick:
        return quick
    if _assign_hits(text) == 1:
        return sniff_blocks(text, git_ignored=is_git_ignored(p))
    return []


# Commands that only ask ABOUT a path (ignored? tracked? exists?) and never print its
# bytes. `git check-ignore .env` was blocked as if it read the file. A segment that also
# substitutes or redirects (`$(…)`, backtick, `<`, `>`) is never treated as metadata-only.
_SEGMENT_SPLIT = re.compile(r"(&&|\|\||[;|\n])")
_METADATA_ONLY = re.compile(
    r"^\s*(?:\w+=\S*\s+)*"
    r"(?:git\s+(?:-C\s+\S+\s+)?(?:check-ignore|ls-files|status)\b|test\s|\[\s|stat\s)"
)
_UNSAFE_IN_SEGMENT = re.compile(r"\$\(|`|[<>]")


def elide_metadata_only(cmd: str) -> str:
    """Blank pipeline segments that only query path metadata, before NAME scanning."""
    parts = _SEGMENT_SPLIT.split(cmd)
    for i in range(0, len(parts), 2):
        seg = parts[i]
        if _METADATA_ONLY.match(seg) and not _UNSAFE_IN_SEGMENT.search(seg):
            parts[i] = " METADATA_ONLY "
    return "".join(parts)


def scan(target: str) -> list[str]:
    """Return list of human-readable match labels (empty = allowed)."""
    hits: list[str] = []
    for label, pat in GENERIC_PATTERNS + load_user_patterns():
        try:
            if re.search(pat, target, flags=re.IGNORECASE | re.DOTALL):
                hits.append(label)
        except re.error:
            hits.append(f"INVALID regex in secret-patterns.txt: {pat}")
    return hits


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        # Fail open on malformed payload — don't break the harness.
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool_name == "Bash":
        target = tool_input.get("command") or ""
    elif tool_name in ("Read", "Write", "Edit", "MultiEdit"):
        # Write/Edit/MultiEdit were unchecked: the hook blocked READING a source
        # file whose name looked secret while leaving WRITES to a real vault file
        # wide open. file_path is the target for all of them.
        target = tool_input.get("file_path") or ""
    else:
        return 0

    if not target:
        return 0

    # Strip references to this hook's own files so editing/cp'ing the hook
    # itself doesn't self-trigger.
    self_ref_re = re.compile(r"\b(secret-patterns(?:\.txt)?|block-secrets(?:\.py)?)\b")
    target_for_scan = self_ref_re.sub("HOOKFILE", target)

    # Strip heredoc bodies and `git commit -m` message text so narrative
    # references (a commit like "fix secrets.yml ref", a documentation blob)
    # don't trip patterns that target actual secret-file access. Shell OUTSIDE
    # the prose is preserved, so a real `cat /etc/shadow` still gets caught.
    target_for_scan = elide_prose(target_for_scan)

    hits = scan(elide_metadata_only(target_for_scan) if tool_name == "Bash" else target_for_scan)

    # Name patterns missed. Fall through to the content sniff — the file's bytes,
    # not its filename. Fails OPEN but LOUDLY: a guard that wedges every Bash call
    # is worse than one that misses.
    sniffed: Path | None = None
    if not hits:
        try:
            cwd = Path(payload.get("cwd") or os.getcwd())
            if tool_name == "Read":
                p = Path(target)
                p = p if p.is_absolute() else cwd / p
                found = sniff_path(p)
                if found:
                    hits, sniffed = found, p
            else:
                for p in candidate_paths(target_for_scan, cwd):
                    found = sniff_path(p)
                    if found:
                        hits, sniffed = found, p
                        break
        except Exception:
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 0

    if not hits:
        return 0

    bullets = "\n".join(f"  • {h}" for h in hits)
    where = f"\nSecret content detected in: {sniffed}\n" if sniffed else ""
    sys.stderr.write(
        "BLOCKED by ~/.claude/hooks/block-secrets.py — this "
        f"{tool_name} call matched secret-exposure patterns:\n"
        f"{bullets}\n{where}\n"
        "Reading credentials, private keys, or secret config files is not "
        "permitted. STOP and surface this to the user. If the user genuinely "
        "needs the file inspected, THEY run the command — not you.\n\n"
        f"Patterns file: {PATTERNS_FILE}\n"
        f"Emergency bypass (user-set, single shell only): export {BYPASS_ENV}=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
