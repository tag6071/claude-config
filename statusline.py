#!/usr/bin/env python3
"""Claude Code status line — no external deps (no jq).
Reads the session JSON on stdin, prints: 📁 <dir> (<branch>) [<model>]."""
import json
import subprocess
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    cwd = data.get("workspace", {}).get("current_dir", "")
    model = data.get("model", {}).get("display_name", "")

    branch = ""
    if cwd:
        try:
            branch = subprocess.run(
                ["git", "-C", cwd, "branch", "--show-current"],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass

    parts = [f"📁 {cwd}" if cwd else "📁"]
    if branch:
        parts[0] += f" ({branch})"
    if model:
        parts.append(f"[{model}]")
    print(" ".join(parts))


if __name__ == "__main__":
    main()
