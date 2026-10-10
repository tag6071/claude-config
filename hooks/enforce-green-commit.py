#!/usr/bin/python3
"""
PreToolUse hook: enforce "no commit without green" by auto-formatting + linting
staged files, then blocking the commit if check-mode issues remain.

Also blocks `git commit --amend` unless CLAUDE_ALLOW_AMEND=1 is set in the
shell environment.

Reads JSON from stdin (Claude Code hook protocol). Exits:
  0 -> allow commit (any auto-fixed files have been re-staged)
  2 -> block commit (stderr shown to Claude)

Design choices:
- Only operates on files already STAGED for this commit. Will not touch
  unrelated files, per CLAUDE.md "one change at a time / smallest possible diff".
- Tool detection is via config-file presence. If no config exists, the hook
  passes silently — fresh repos can still commit. Scaffolding a project with
  proper tooling is a separate concern (see the scaffold skill).
- Auto-fix is applied where the tool supports it; check-mode is then run to
  catch anything that couldn't be fixed.
- Opt-out: set CLAUDE_SKIP_GREEN_HOOK=1 to bypass entirely (single shell).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BYPASS_ENV = "CLAUDE_SKIP_GREEN_HOOK"
AMEND_OK_ENV = "CLAUDE_ALLOW_AMEND"


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"


def get_repo_root() -> Path | None:
    rc, out = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if rc != 0:
        return None
    return Path(out)


def get_staged_files(repo: Path) -> list[str]:
    rc, out = run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], repo
    )
    if rc != 0:
        return []
    return [f for f in out.splitlines() if f]


def has_config(repo: Path, *names: str) -> bool:
    return any((repo / n).exists() for n in names)


def has_ruff_config(repo: Path) -> bool:
    if has_config(repo, "ruff.toml", ".ruff.toml"):
        return True
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        try:
            return "[tool.ruff" in pyproject.read_text()
        except Exception:
            return False
    return False


def has_prettier_config(repo: Path) -> bool:
    return has_config(
        repo,
        ".prettierrc", ".prettierrc.json", ".prettierrc.yaml",
        ".prettierrc.yml", ".prettierrc.js", "prettier.config.js",
        "prettier.config.mjs", "prettier.config.cjs",
    )


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    if os.environ.get(BYPASS_ENV) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""

    # Block --amend unless explicitly allowed.
    if re.search(r"\bgit\s+commit\b[^\n]*\s--amend\b", command):
        if os.environ.get(AMEND_OK_ENV) != "1":
            sys.stderr.write(
                "BLOCKED: git commit --amend.\n"
                "Prefer a NEW commit over amending. "
                "Amending rewrites history and can destroy prior work if a pre-commit "
                "hook later fails.\n"
                f"Single-shell override: export {AMEND_OK_ENV}=1\n"
            )
            return 2
        # Fall through — still want to format/lint amended commits.

    # Only act on `git commit` (not other git commands).
    if not re.search(r"\bgit\s+commit\b", command):
        return 0

    repo = get_repo_root()
    if not repo:
        return 0

    staged = get_staged_files(repo)
    if not staged:
        # Let git's own "nothing to commit" message fire.
        return 0

    # scripts/lint-checks/ holds byte-exact, library-owned check copies whose
    # sha256 is recorded in .installed-versions (the install-lint-rails manifest).
    # Reformatting them (shfmt/ruff/biome) breaks that invariant — the next
    # `/install-lint-rails` re-run would misread them as locally edited. Never
    # auto-format them in ANY repo.
    def by_ext(*exts: str) -> list[str]:
        return [
            f
            for f in staged
            if f.endswith(exts) and "scripts/lint-checks/" not in f
        ]

    auto_fixed: list[str] = []
    check_failures: list[tuple[str, str]] = []

    # Python: ruff (format + lint --fix, then lint check)
    py = by_ext(".py", ".pyi")
    if py and has_ruff_config(repo) and tool_available("ruff"):
        run(["ruff", "format", *py], repo)
        run(["ruff", "check", "--fix", *py], repo)
        auto_fixed.extend(py)
        rc, out = run(["ruff", "check", *py], repo)
        if rc != 0:
            check_failures.append(("ruff check", out))

    # Web: biome (format --write + lint --write, then lint check)
    web = by_ext(".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".json", ".jsonc", ".css")
    if web and has_config(repo, "biome.json", "biome.jsonc") and tool_available("biome"):
        run(["biome", "format", "--write", *web], repo)
        run(["biome", "lint", "--write", *web], repo)
        auto_fixed.extend(web)
        rc, out = run(["biome", "lint", *web], repo)
        if rc != 0:
            check_failures.append(("biome lint", out))

    # Rust: cargo fmt + (optionally) clippy
    rs = by_ext(".rs")
    if rs and has_config(repo, "Cargo.toml") and tool_available("cargo"):
        run(["cargo", "fmt"], repo)
        auto_fixed.extend(rs)
        if os.environ.get("CLAUDE_RUN_CLIPPY") == "1":
            rc, out = run(["cargo", "clippy", "--", "-D", "warnings"], repo)
            if rc != 0:
                check_failures.append(("cargo clippy", out))

    # Go: gofmt + go vet
    go = by_ext(".go")
    if go and has_config(repo, "go.mod") and tool_available("gofmt"):
        run(["gofmt", "-w", *go], repo)
        auto_fixed.extend(go)
        if tool_available("go"):
            rc, out = run(["go", "vet", "./..."], repo)
            if rc != 0:
                check_failures.append(("go vet", out))

    # Shell: shfmt + shellcheck
    sh = by_ext(".sh", ".bash")
    if sh and tool_available("shfmt"):
        run(["shfmt", "-w", *sh], repo)
        auto_fixed.extend(sh)
    if sh and tool_available("shellcheck"):
        rc, out = run(["shellcheck", *sh], repo)
        if rc != 0:
            check_failures.append(("shellcheck", out))

    # Markdown / HTML: prettier (only if project actually configures it)
    md = by_ext(".md", ".html")
    if md and has_prettier_config(repo) and tool_available("prettier"):
        run(["prettier", "--write", *md], repo)
        auto_fixed.extend(md)

    # Re-stage anything we touched (deduped, preserving order).
    if auto_fixed:
        unique = list(dict.fromkeys(auto_fixed))
        run(["git", "add", "--", *unique], repo)

    if check_failures:
        msg = ["BLOCKED: commit has lint issues that could not be auto-fixed:\n"]
        for label, out in check_failures:
            msg.append(f"--- {label} ---")
            msg.append(out or "(no output)")
            msg.append("")
        msg.append("Fix the issues above, re-stage, and retry the commit.")
        msg.append(f"Bypass (single shell): export {BYPASS_ENV}=1")
        sys.stderr.write("\n".join(msg) + "\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
