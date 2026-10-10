#!/usr/bin/python3
"""
PreToolUse:Bash guard — no git commit may carry an unapproved author identity.

THE DEFECT THIS EXISTS FOR: a Claude Code session authored 27 commits
across two repos as `yourname <you@example.com>` — the user's PERSONAL email —
by running:

    git -c user.email=you@example.com -c user.name=yourname commit -m "..."

`-c` overrides config for that one process. It leaves nothing behind: ~/.gitconfig
still said `your-git-user`, no GIT_AUTHOR_* env var existed, no repo had a local override,
and a fresh commit resolved to the correct identity. The leak was INVISIBLE to every
config-level check. That is why this guard reads the COMMAND STRING, not the config:
a setting cannot defend against a flag that outranks it.

Five injection routes, all blocked unless the value is allowlisted:
  R1  env prefix          GIT_AUTHOR_EMAIL=x git commit
  R2  cmdline config      git -c user.email=x commit
  R3  explicit author     git commit --author="x <y>"
  R4  config write        git config user.email x
  R5  history rewrite     filter-branch --env-filter '...GIT_AUTHOR_EMAIL=x...'

Allowlist: git-identity-allow.txt (sibling). Exit: 0 allow · 2 block.
"""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

from hook_common import elide_prose

HOOKS_DIR = Path(__file__).resolve().parent
ALLOW_FILE = HOOKS_DIR / "git-identity-allow.txt"
BYPASS_ENV = "CLAUDE_ALLOW_GIT_IDENTITY"

# Subcommands that WRITE history — an identity reaching one of these is what we care
# about. `git log --author=x` merely FILTERS and must stay free (the audit that FOUND
# this leak greps history for the personal email; blocking that would be self-defeating).
WRITING_SUBCMDS = {
    "commit", "am", "cherry-pick", "revert", "rebase", "merge", "tag",
    "filter-branch", "filter-repo", "config",
}
# git options that take their value as a SEPARATE token — the subcommand is the first
# bare word after these are consumed. `-c` is the one that carried the original leak:
# in `git -c user.email=x commit`, a naive scan sees `user.email=x` where `commit` should
# be, concludes "not a writing command", and waves the injection straight through.
OPTS_WITH_VALUE = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
# Shell separators — an injection in one pipeline segment must not be judged against
# (or excused by) the text of another.
SEGMENT_SPLIT = re.compile(r"\|\||&&|[|;&\n]")

R2 = re.compile(r"-c\s+(user\.(?:email|name))\s*=\s*(\S+)", re.I)
R1 = re.compile(r"\b(GIT_(?:AUTHOR|COMMITTER)_(?:EMAIL|NAME))\s*=\s*(\"[^\"]*\"|'[^']*'|\S+)")
R3 = re.compile(r"--author\s*=?\s*(\"[^\"]*\"|'[^']*'|\S+)", re.I)
R4 = re.compile(
    r"\bgit\b[^|;&\n]*?\bconfig\b[^|;&\n]*?\b(user\.(?:email|name))\s+(\"[^\"]*\"|'[^']*'|\S+)",
    re.I,
)
# Any email-shaped token, used as the last-resort sweep inside a writing command.
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def allowed() -> set[str]:
    if not ALLOW_FILE.exists():
        return set()
    out = set()
    for line in ALLOW_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line.lower())
    return out


def unquote(v: str) -> str:
    return v.strip().strip("\"'").strip()


def names_and_emails(value: str) -> list[str]:
    """`"yourname <a@b.com>"` -> ['yourname', 'a@b.com']. A bare value -> itself."""
    v = unquote(value)
    m = re.match(r"^(.*?)\s*<([^>]+)>$", v)
    if m:
        return [p.strip() for p in (m.group(1), m.group(2)) if p.strip()]
    return [v] if v else []


def git_subcommand(segment: str) -> str | None:
    """The subcommand of a git invocation, skipping global options AND their values.

    Returns None if the segment isn't a git call. Tokenizing (not regex-matching) is
    what makes `git -c user.email=x commit` resolve to 'commit' rather than to the
    override's value — the precise miss that let the original leak through.
    """
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()  # unbalanced quotes: degrade, don't crash

    i = 0
    while i < len(tokens):
        if tokens[i] == "git" or tokens[i].endswith("/git"):
            break
        i += 1
    else:
        return None

    i += 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in OPTS_WITH_VALUE:
            i += 2  # consume the option AND its detached value
        elif tok.startswith("-"):
            i += 1
        else:
            return tok
        continue
    return None


def main() -> int:
    import os

    if os.environ.get(BYPASS_ENV) == "1":
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # unparseable payload: fail open, don't break the harness
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if "git" not in command:
        return 0

    # PROSE THAT MENTIONS an email is not an identity injection: `git commit -m "fix
    # bounces to support@acme.com"` must not trip the R5 sweep. Blank heredoc bodies
    # and commit-message text; the shell AROUND them (where -c/--author live) survives.
    command = elide_prose(command)

    ok = allowed()
    hits: list[str] = []

    def check(route: str, raw: str) -> None:
        for part in names_and_emails(raw):
            if part.lower() not in ok:
                hits.append(f"{route}: identity {part!r} is not allowlisted")

    # R1 is judged on the whole command: an exported GIT_AUTHOR_* is a loaded gun even
    # when the git call that fires it lands in a later segment (or a later turn).
    for _, val in R1.findall(command):
        check("R1 env-prefix override", val)

    # R2-R5 are judged PER SEGMENT, and only where git actually writes history — so the
    # audit pipeline `git log --format='%ae' | grep <personal>` stays runnable while
    # `git -c user.email=<personal> commit` does not.
    for segment in SEGMENT_SPLIT.split(command):
        if git_subcommand(segment) not in WRITING_SUBCMDS:
            continue
        for _, val in R2.findall(segment):
            check("R2 `-c user.*` cmdline override", val)
        for val in R3.findall(segment):
            check("R3 `--author=`", val)
        for _, val in R4.findall(segment):
            check("R4 `git config user.*` write", val)
        # R5 sweep: any unapproved email inside a history-writing git call. Catches
        # env-filter payloads and any injection shape the routes above don't model.
        for em in EMAIL.findall(segment):
            if em.lower() not in ok and not any(em in h for h in hits):
                hits.append(f"R5 unapproved email in a history-writing git command: {em!r}")

    if not hits:
        return 0

    bullets = "\n".join(f"  • {h}" for h in dict.fromkeys(hits))
    allowlist = ", ".join(sorted(ok)) or "(empty!)"
    sys.stderr.write(
        "BLOCKED by ~/.claude/hooks/git-identity-guard.py — this command would commit "
        "under an identity the user has not approved:\n"
        f"{bullets}\n\n"
        "NEVER inject a git identity on the command line. Do not pass `-c user.email=`, "
        "`--author=`, or GIT_AUTHOR_*/GIT_COMMITTER_* to git. Let the repo's configured "
        "identity flow through untouched — run the command again with the override REMOVED.\n\n"
        "The user's personal email must never appear as a git author. Once this "
        "exact pattern put it on 27 commits.\n\n"
        f"Allowlisted identities: {allowlist}\n"
        f"Allowlist file: {ALLOW_FILE}\n"
        f"Bypass (USER-set only, single shell): export {BYPASS_ENV}=1\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
