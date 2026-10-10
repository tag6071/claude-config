#!/usr/bin/env python3
"""Warn on race-language comments inside untagged Playwright tests.

If a `test(...)` block contains race-flavoured language ("race
condition", "Run alone", "deterministic when", "may flake", etc.) AND
the test name lacks a `@serial`, `@quarantined`, `@hardware`, or
`@slow` tag, that's a flake admission with no isolation.

The check attributes leading comments (within ~20 lines above a
test() decl) to the FOLLOWING test, so a comment block that
explains the next test's `@serial` reason doesn't get mis-attributed
to the prior test.

Exits 0 always (WARN-only).
"""
from __future__ import annotations

import glob
import re
import sys

RACE = re.compile(
    r"race condition|run alone|deterministic when|may flake"
    r"|known flake|racy by design",
    re.IGNORECASE,
)
# Backreference (?P=q) keeps the closing quote matching the opener so
# a name like `"clicking 'turn on'..."` doesn't truncate at the apostrophe.
TEST_DECL = re.compile(r"""^\s*test\s*[(]\s*(?P<q>["'])(.+?)(?P=q)""")
TAGS = ("@serial", "@quarantined", "@hardware", "@slow")


def main() -> int:
    warnings: list[str] = []
    spec_globs = (
        glob.glob("tests/*.spec.mjs")
        + glob.glob("tests/*.spec.ts")
        + glob.glob("tests/*.spec.js")
        + glob.glob("tests/**/*.spec.mjs", recursive=True)
        + glob.glob("tests/**/*.spec.ts", recursive=True)
        + glob.glob("tests/**/*.spec.js", recursive=True)
    )
    for f in sorted(set(spec_globs)):
        try:
            lines = open(f, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        tests = []
        for i, line in enumerate(lines):
            tm = TEST_DECL.match(line)
            if not tm:
                continue
            name = tm.group(2)
            tagged = any(t in name for t in TAGS)
            tests.append((i, name, tagged))
        for i, line in enumerate(lines):
            if not RACE.search(line):
                continue
            next_test = next(((idx, n, t) for idx, n, t in tests if idx > i), None)
            prev_test = None
            for entry in tests:
                if entry[0] <= i:
                    prev_test = entry
                else:
                    break
            if next_test and (next_test[0] - i) <= 20:
                chosen = next_test
            else:
                chosen = prev_test
            if chosen is None:
                continue
            _, name, tagged = chosen
            if tagged:
                continue
            warnings.append(
                f"{f}:{i+1}: race-language in untagged test "
                f"`{name}` — fix or tag it"
            )
    if warnings:
        print("test files with race-language but no @quarantined/@serial tag:")
        for w in warnings:
            print(w)
        print("↳ either fix the race or tag the test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
