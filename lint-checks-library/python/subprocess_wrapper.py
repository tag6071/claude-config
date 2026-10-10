"""External-CLI wrapper discipline.

If your project has a dedicated wrapper for shelling out to a specific
external binary (e.g. `_claude.py` wrapping `claude`), every OTHER
module should route through it rather than calling `subprocess.run(["claude", ...])`
directly. This keeps redaction / error-handling / event-emission centralized.

CONFIGURED PER PROJECT: edit the WRAPPERS dict below to declare your
specific CLI → wrapper-module mappings. Default ships empty; set it up
once after `/install-lint-rails` based on your project's shell-outs.

Example:
    WRAPPERS = {
        "claude":   "tools/_claude.py",
        "exiftool": "tools/_exiftool.py",
        "kubectl":  "tools/_kubectl.py",
    }

Exits 1 on violation.
"""
from __future__ import annotations

import glob
import re
import sys

# === Project-specific config — edit per repo ===
WRAPPERS: dict[str, str] = {
    # "claude": "tools/_claude.py",
    # "exiftool": "tools/_exiftool.py",
}
# === End config ===


def main() -> int:
    if not WRAPPERS:
        # Empty config — nothing to enforce. Silent pass.
        return 0
    violations: list[str] = []
    py_files = (
        glob.glob("tools/*.py")
        + glob.glob("src/**/*.py", recursive=True)
        + glob.glob("*.py")
    )
    for f in sorted(set(py_files)):
        # Skip the wrapper files themselves
        if f in WRAPPERS.values():
            continue
        try:
            text = open(f, encoding="utf-8").read()
        except OSError:
            continue
        for cli, wrapper in WRAPPERS.items():
            # Match `"<cli>"` or `'<cli>'` as a list element / argv token,
            # which is how subprocess invocations spell it.
            pat = re.compile(
                rf'(?:\[|,|\()\s*["\']{re.escape(cli)}["\']'
            )
            for line_no, line in enumerate(text.splitlines(), 1):
                if pat.search(line):
                    violations.append(
                        f"{f}:{line_no}: shells out to `{cli}` directly — "
                        f"route through {wrapper}"
                    )
    if violations:
        print("external CLI shell-out outside its dedicated wrapper:")
        for v in violations:
            print(v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
