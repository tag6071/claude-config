#!/usr/bin/python3
"""
Table tests for frontend-guard.blank_comments().

No pytest dependency (native first). Run standalone:
    python3 ~/.claude/hooks/test_frontend_guard.py
Exits 0 all-pass / 1 on failure.

Loaded via importlib because the module filename has a hyphen.

Why this exists: the guard used to read a GitHub issue ref in a comment
(`// react-rnd issue #984`) as a raw hex colour and block the write. The fix
blanks comment CONTENT before scanning. The NEGATIVE cases below matter most —
a guard narrowed until it stops catching real violations is worse than the false
positive it was narrowed to fix.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "frontend_guard", Path(__file__).with_name("frontend-guard.py")
)
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

HEX = next(pat for label, pat, _, _ in fg.RULES if "colour" in label)
INLINE = next(pat for label, pat, _, _ in fg.RULES if "inline style" in label)

# (name, source lines, regex, should_still_match_after_blanking)
CASES = [
    # --- the false positives this fix exists to kill ---
    ("issue ref in line comment", ["// react-rnd issue #984, open"], HEX, False),
    ("hex in block comment", ["/* brand was #ff0000 before */"], HEX, False),
    ("hex in multi-line block", ["/* old palette:", "   #abc123", "*/"], HEX, False),
    ("trailing comment after code", ['const a = 1; // note #123'], HEX, False),
    # --- NEGATIVE: real violations must STILL be caught ---
    ("real hex in live code", ['<div data-c="#ff0000" />'], HEX, True),
    ("real rgba in live code", ['const c = "rgba(0,0,0,.5)";'], HEX, True),
    ("url must not swallow a real violation on the same line",
     ['const l = "https://x.com"; const bad = "#ff0000";'], HEX, True),
    ("inline style still caught", ["<div style={{ color: 'red' }} />"], INLINE, True),
    ("hex after a block comment closes", ["/* c */ const c = '#ff0000';"], HEX, True),
    # --- a URL alone is not a violation and not a comment ---
    ("bare url is untouched", ['const u = "https://x.com/a";'], HEX, False),
]


def main() -> int:
    failed = 0
    for name, lines, pat, want in CASES:
        blanked = fg.blank_comments(lines)
        got = any(pat.search(ln) for ln in blanked)
        if got != want:
            print(f"FAIL {name}: want match={want}, got {got} — blanked={blanked!r}")
            failed += 1
        # line count must survive: hit messages cite L numbers
        if len(blanked) != len(lines):
            print(f"FAIL {name}: line count {len(lines)} -> {len(blanked)}")
            failed += 1

    total = len(CASES)
    if failed:
        print(f"\n{failed} failed / {total} cases")
        return 1
    print(f"all {total} cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
