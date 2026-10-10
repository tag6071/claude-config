#!/usr/bin/python3
"""
Table tests for app-lock-guard.is_lock().

No pytest dependency (native first). Run standalone:
    python3 ~/.claude/hooks/test_app_lock_guard.py
Exits 0 all-pass / 1 on failure.

The NEGATIVE cases matter most: unlocking, normal chmod, and prose that merely
mentions a lock must never block.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS))
spec = importlib.util.spec_from_file_location("app_lock_guard", HOOKS / "app-lock-guard.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

CASES: list[tuple[str, bool, str]] = [
    # ---- BLOCK ----
    ("chflags uchg ~/SomeApp/modes/default.json ~/SomeApp/modes/pro.json", True, "lock app config"),
    ("M=~/x; chflags uchg $M/a.json", True, "after a separator"),
    ("sudo chflags schg /Library/Preferences/x.plist", True, "system immutable via sudo"),
    ("chflags -R uchg ~/Library/Application\\ Support/App", True, "recursive flag before mode"),
    ("chattr +i /etc/app.conf", True, "linux immutable"),
    ("chmod a-w ~/Library/Preferences/com.app.plist", True, "symbolic remove write"),
    ("chmod -w config.json", True, "bare -w"),
    ("chmod 444 settings.json", True, "octal read-only"),
    ("chmod 0555 ~/app/settings", True, "4-digit octal, owner r-x"),
    ("find ~/app -name '*.json' | xargs chmod u-w", True, "via xargs"),
    # ---- ALLOW ----
    ("chflags nouchg ~/SomeApp/modes/*.json", False, "unlock"),
    ("chflags hidden ~/thing", False, "non-immutable flag"),
    ("chattr -i /etc/app.conf", False, "linux unlock"),
    ("chmod +x script.sh", False, "make executable"),
    ("chmod 755 bin/tool", False, "normal exec"),
    ("chmod 644 notes.txt", False, "normal file"),
    ("chmod 600 ~/.netrc", False, "private but owner-writable"),
    ("chmod go-w shared.txt", False, "only group/other lose write"),
    ("chmod 400 ~/.ssh/id_ed25519", False, "ssh key exemption"),
    ("chmod 400 server.pem", False, "pem key exemption"),
    ("git commit -m 'stop using chflags uchg on app config'", False, "prose in commit msg"),
    ("grep -rn 'chflags uchg' hooks/", False, "quoted search arg"),
    ("echo done", False, "unrelated"),
]


def main() -> int:
    fails = 0
    for cmd, want, note in CASES:
        got = g.is_lock(cmd)
        if got != want:
            fails += 1
            print(f"FAIL [{note}] want={want} got={got}: {cmd}")
    print(f"{len(CASES) - fails}/{len(CASES)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
