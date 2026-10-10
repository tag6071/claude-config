"""The guard has to catch the message that started this and stay silent on everything else."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "dead_end_guard", Path(__file__).with_name("dead-end-guard.py")
)
g = importlib.util.module_from_spec(spec)
sys.modules["dead_end_guard"] = g
spec.loader.exec_module(g)

P = Path("app.py")


def test_catches_the_message_that_started_this():
    src = 'print("Device not reachable — connect it, then retry.")\n'
    assert g.flagged(P, src)


def test_silent_once_the_command_is_attached():
    src = (
        'print("Device not reachable — join the same network, then retry: "\n'
        '      "`mytool status`.")\n'
    )
    assert not g.flagged(P, src)


def test_catches_a_dead_end_split_across_wrapped_lines():
    """The formatter splits the long messages, and the long ones explain the failures."""
    src = (
        "raise SystemExit(\n"
        '    "could not reach the device — "\n'
        '    "check your connection"\n'
        ")\n"
    )
    assert g.flagged(P, src)


def test_ui_path_counts_as_an_exit():
    src = 'toast("Sync is off — Settings → Advanced → Sync")\n'
    assert not g.flagged(P, src)


def test_link_counts_as_an_exit():
    src = 'console.error("Something went wrong — see https://example.test/fix-it")\n'
    assert not g.flagged(P, src)


def test_ignores_comments_and_docstrings():
    src = (
        '# something went wrong here once; check the logs of the old runs\n'
        '"""Retry semantics: the caller may try again, check your config first."""\n'
    )
    assert not g.flagged(P, src)


def test_ignores_a_plain_report_with_no_promise():
    src = 'print(f"described {n} image(s) across {outdir}")\n'
    assert not g.flagged(P, src)


def test_ignores_a_non_printing_line():
    src = 'MESSAGE_TEMPLATE = "try again"  # assembled elsewhere, printed with its exit\n'
    assert not g.flagged(P, src)


if __name__ == "__main__":
    tests = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError:
            failed += 1
            print(f"FAIL  {t.__name__}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
