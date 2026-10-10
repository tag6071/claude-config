#!/usr/bin/python3
"""
Table tests for block-secrets content sniff.

No pytest dependency (native first). Run standalone:
    python3 ~/.claude/hooks/test_block_secrets.py
Exits 0 all-pass / 1 on failure.

BOOTSTRAP PARADOX: this file must contain a private-key header to test for one.
If the literal appeared verbatim on disk, the sniff would block reads of its own
test suite. So the header is assembled at runtime and never written out. The
hooks dir is ALSO exempt from sniffing (belt and braces) — see SNIFF_EXEMPT_DIRS.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("block_secrets", HOOKS / "block-secrets.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

DASH = "-" * 5
PEM_OPEN = f"{DASH}BEGIN RSA PRIVATE" + f" KEY{DASH}"
PEM_CLOSE = f"{DASH}END RSA PRIVATE" + f" KEY{DASH}"

PLACEHOLDER_SAFE = """
sso_issuer_key: "{{ vault_sso_issuer_key }}"
client_secret: CHANGEME
password: <your-password-here>
api_key: ${API_KEY}
db_password: ""
"""

REAL_OIDC = f"""
sso_clients:
  - id: myapp
    secret: '$plaintext$K9fLm2xQwErTyUiOpAsDfGhJkL'
sso_issuer_key: |
  {PEM_OPEN}
  MIIEowIBAAKCAQEA3Zx8kQ2vN1pLmXyR7tGhAAAAB3NzaC1yc2EAAAADAQABAAAB
  {PEM_CLOSE}
"""

VAULTED = "$ANSIBLE_VAULT;1.1;AES256\n33613262666564383163\n"

DOCS_PROSE = f"""
# How to rotate the key: look for `{DASH}BEGIN` markers, then run ssh-keygen.
See the password rotation policy. secret: see vault.
"""

COVERAGE_JSON = '{"totals": {"percent_covered": 91.2}, "files": {}}'

TWO_ASSIGNMENTS = """
smtp_password: hunter2hunter2
api_token: abcdefgh12345678
"""

ONE_ASSIGNMENT = "POSTGRES_PASSWORD: postgresqlpw\n"

# Source that merely PASSES secrets around holds none — the value is code, not a
# literal. Blocking it made a provisioning script unreadable AND unpatchable
# (a real false positive). Three matches here, zero of them a secret.
CODE_REFERENCES = """
NOTIFY_TOKEN = os.environ.get("NOTIFY_TOKEN", "").strip()
api.add_notification(notifyToken=NOTIFY_TOKEN, notifyChannel=CHANNEL)
api.test_notification(notifyToken=NOTIFY_TOKEN)
client_secret = self.credentials.client_secret
api_key: process.env.LOOKUP_KEY
API_KEY=$(read_vault router_api_key)
API_SECRET=`read_vault router_api_secret`
"""

# ...but a literal in the same trailing-comma SHAPE is still a secret.
LITERAL_IN_KWARG = """
    password=hunter2hunter,
    api_token=abcdefgh12345678,
"""

# (name, text, git_ignored, expect_block)
CASES = [
    ("code references, not literals", CODE_REFERENCES, False, False),
    ("code references, git-ignored file", CODE_REFERENCES, True, False),
    ("literal values in kwarg position", LITERAL_IN_KWARG, False, True),
    ("placeholder-safe", PLACEHOLDER_SAFE, False, False),
    ("real oidc.yml shape", REAL_OIDC, False, True),
    ("ansible-vault payload", VAULTED, False, True),
    ("docs prose", DOCS_PROSE, False, False),
    ("coverage.json", COVERAGE_JSON, False, False),
    ("two secret assignments", TWO_ASSIGNMENTS, False, True),
    ("one assignment, tracked", ONE_ASSIGNMENT, False, False),
    ("one assignment, git-ignored", ONE_ASSIGNMENT, True, True),
    ("empty", "", False, False),
]


def main() -> int:
    fails = 0

    for name, text, ignored, expect in CASES:
        got = bool(bs.sniff_blocks(text, git_ignored=ignored))
        if got != expect:
            fails += 1
            verb = "BLOCK" if expect else "allow"
            print(f"FAIL  expected={verb:5} got={'BLOCK' if got else 'allow':5}  {name}")
            print(f"      signals: {bs.sniff_secret(text)}")

    # is_git_ignored against a real repo: ~/.claude is one.
    tracked = HOOKS / "bash-guard.py"
    if bs.is_git_ignored(tracked):
        fails += 1
        print("FAIL  is_git_ignored said a TRACKED file is ignored")

    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        subprocess.run(["git", "init", "-q"], cwd=dp, check=True)
        (dp / ".gitignore").write_text("ignored.yml\n")
        ig = dp / "ignored.yml"
        ig.write_text(ONE_ASSIGNMENT)
        if not bs.is_git_ignored(ig):
            fails += 1
            print("FAIL  is_git_ignored missed a genuinely ignored file")

        # non-repo => exit 128 => must read as "not ignored", not crash
        with tempfile.TemporaryDirectory() as nd:
            stray = Path(nd) / "x.yml"
            stray.write_text("hi\n")
            if bs.is_git_ignored(stray):
                fails += 1
                print("FAIL  is_git_ignored returned True outside a git repo")

        # end-to-end: sniff_path blocks the git-ignored one-assignment file
        if not bs.sniff_path(ig):
            fails += 1
            print("FAIL  sniff_path did not block a git-ignored secret file")

        # candidate_paths finds it from a `sed -n 1,60p` command
        cands = bs.candidate_paths("sed -n 1,60p ignored.yml", dp)
        if ig.resolve() not in [c.resolve() for c in cands]:
            fails += 1
            print(f"FAIL  candidate_paths missed ignored.yml (got {cands})")

        # unbalanced quotes must not raise
        try:
            bs.candidate_paths("ssh h \"docker exec x sh -c 'cat /a/b.yml'\"", dp)
        except Exception as e:
            fails += 1
            print(f"FAIL  candidate_paths raised on unbalanced quotes: {e}")

        # cheap gate: no path-ish token => zero work
        if bs.candidate_paths("git status", dp):
            fails += 1
            print("FAIL  candidate_paths did work on a no-path command")

    # bootstrap paradox: the hook must never block its own source or tests
    for own in (HOOKS / "block-secrets.py", HOOKS / "test_block_secrets.py"):
        if bs.sniff_path(own):
            fails += 1
            print(f"FAIL  hook blocks its own source: {own.name}")

    fails += e2e()

    total = len(CASES) + 18
    if fails:
        print(f"\n{fails} FAILED")
        return 1
    print(f"{total}/{total} passed")
    return 0


def _run_hook(hook: str, payload: dict) -> int:
    """Drive the real hook as a subprocess, exactly as Claude Code does."""
    import json

    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    ).returncode


def e2e() -> int:
    """Regression pin: the actual leak. A fake key, never the real one."""
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        subprocess.run(["git", "init", "-q"], cwd=dp, check=True)
        name = "oi" + "dc.yml"  # keep the literal out of any shell command line
        (dp / ".gitignore").write_text(f"{name}\n")
        (dp / name).write_text(REAL_OIDC)
        (dp / "README.md").write_text("# hello\nnothing secret here\n")

        # Bash path: the exact command shape that leaked the key.
        rc = _run_hook(
            "block-secrets.py",
            {"tool_name": "Bash", "cwd": str(dp),
             "tool_input": {"command": f"sed -n 1,60p {name}"}},
        )
        if rc != 2:
            fails += 1
            print(f"FAIL  e2e Bash sed-on-secret: expected rc=2 got {rc}")

        # Read path.
        rc = _run_hook(
            "block-secrets.py",
            {"tool_name": "Read", "tool_input": {"file_path": str(dp / name)}},
        )
        if rc != 2:
            fails += 1
            print(f"FAIL  e2e Read secret: expected rc=2 got {rc}")

        # Negative: an innocent file must sail through, or the guard is useless.
        rc = _run_hook(
            "block-secrets.py",
            {"tool_name": "Bash", "cwd": str(dp),
             "tool_input": {"command": "cat README.md"}},
        )
        if rc != 0:
            fails += 1
            print(f"FAIL  e2e cat README.md: expected rc=0 got {rc}")

        rc = _run_hook(
            "block-secrets.py",
            {"tool_name": "Bash", "cwd": str(dp), "tool_input": {"command": "git status"}},
        )
        if rc != 0:
            fails += 1
            print(f"FAIL  e2e git status: expected rc=0 got {rc}")

        # Metadata-only queries never print bytes: allowed. Reading still blocks.
        env = "." + "env"
        for cmd, want in [
            (f"git check-ignore -v {env} || echo not-ignored", 0),
            (f"test -e {env} && echo present", 0),
            (f"git ls-files | grep -c {env}", 2),           # grep segment still scanned
            (f"git check-ignore {env} && cat {env}", 2),    # cat segment still blocks
            (f"test -n \"$(cat {env})\"", 2),               # substitution reads the file
            (f"stat {env} > out.txt", 2),                   # redirect = not metadata-only
        ]:
            rc = _run_hook(
                "block-secrets.py",
                {"tool_name": "Bash", "cwd": str(dp), "tool_input": {"command": cmd}},
            )
            if rc != want:
                fails += 1
                print(f"FAIL  e2e metadata-only {cmd!r}: expected rc={want} got {rc}")
    return fails


if __name__ == "__main__":
    sys.exit(main())
