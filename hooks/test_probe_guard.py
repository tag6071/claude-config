#!/usr/bin/python3
"""
Table tests for probe-guard.classify().

No pytest dependency (native first). Run standalone:
    python3 ~/.claude/hooks/test_probe_guard.py
Exits 0 all-pass / 1 on failure.

Loaded via importlib because the module filename has a hyphen.
The NEGATIVE cases matter most: a guard that blocks everything is
indistinguishable from one that works.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("probe_guard", HOOKS / "probe-guard.py")
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)

# (command, expected_verdict, note)
CASES: list[tuple[str, str, str]] = [
    # ---- BLOCK: rate counters read once ----
    (
        'ssh homeserver "docker stats --no-stream"',
        "block",
        "no --format => default table includes CPU %",
    ),
    (
        "ssh homeserver \"docker stats --no-stream --format '{{.CPUPerc}}'\"",
        "block",
        "explicit CPU request",
    ),
    (
        "docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}' | sort -h -r",
        "block",
        "the exact shape that produced '174% CPU'",
    ),
    ("docker stats --no-stream # sleep", "block", "substring escape must NOT work"),
    ("docker stats --no-stream # for i in 1 2 3; do", "block", "comment is not a loop body"),
    ("top -bn1 | head -20", "block", "top -bn1 %CPU is meaningless"),
    ("top -b -n 1", "block", "spaced form of -bn1"),
    # ---- ALLOW: gauges, and real multi-sampling ----
    (
        "ssh homeserver \"docker stats --no-stream --format '{{.MemUsage}}'\"",
        "allow",
        "MEMORY IS A GAUGE. If this blocks, the guard is wrong, not the command.",
    ),
    (
        "docker stats --no-stream --format '{{.Name}} {{.NetIO}} {{.BlockIO}}'",
        "allow",
        "net/block io are gauges too",
    ),
    (
        "for i in 1 2 3; do docker stats --no-stream --format '{{.CPUPerc}}'; sleep 2; done",
        "allow",
        "structural loop + sleep = deliberate multi-sample",
    ),
    (
        "while true; do docker stats --no-stream; sleep 1; done",
        "allow",
        "while-loop form",
    ),
    ("top -bn2 | tail -n +8", "allow", "two iterations"),
    ("htop", "allow", "word boundary must not match htop"),
    # ---- ADVISE: peeks ----
    (
        "ssh homeserver \"docker exec app sh -c 'tail -c 2000 /var/log/app/alerts.json'\"",
        "advise",
        "THE SIEM command. Remote + in-container: unstat-able. Must still fire.",
    ),
    ("head -c 4096 /var/log/big.log", "advise", "byte slicing a named file"),
    (
        "tail -c 2000 alerts.json | grep -o 'groups' | sort | uniq -c",
        "advise",
        "aggregating a truncated input does NOT un-truncate it",
    ),
    ("sed -n 1,60p config/oidc.yml", "advise", "the form that leaked the key"),
    ("sed -n '10,20p' file.txt", "advise", "quoted range form"),
    ("iostat", "advise", "no interval => since-boot total"),
    ("vmstat", "advise", ""),
    ("sar -u", "advise", ""),
    # ---- ALLOW: legitimate peeks and reads ----
    ("head -c 512 /bin/ls", "allow", "magic-byte sniff, below 1000-byte threshold"),
    ("grep -o 'x' f | sort | uniq -c | head -20", "allow", "bare head = display truncation"),
    ("sort f | uniq -c | tail -5", "allow", "bare tail on stdin"),
    ("iostat 1 2", "allow", "explicit interval"),
    ("vmstat 1 5", "allow", ""),
    ("cat README.md", "allow", ""),
    ("git status --short", "allow", "the hot path: must be untouched"),
    ("tail -f /var/log/syslog", "allow", "follow mode is not a peek"),
    ("sed -n '/pattern/p' file", "allow", "pattern sed, not a line range"),
]


def main() -> int:
    fails = 0
    for cmd, expected, note in CASES:
        got, reason, _fix = pg.classify(cmd, cwd=str(HOOKS))
        if got != expected:
            fails += 1
            print(f"FAIL  expected={expected:6} got={got:6}  {cmd}")
            if note:
                print(f"      note: {note}")
            if reason:
                print(f"      guard said: {reason}")

    # -n peek on a genuinely large local file (needs a real file to stat)
    with tempfile.TemporaryDirectory() as d:
        big = Path(d) / "big.log"
        big.write_bytes(b"x\n" * 600_000)  # ~1.2 MB
        small = Path(d) / "small.log"
        small.write_text("hello\n")

        got, _, _ = pg.classify(f"tail -n 20 {big}", cwd=d)
        if got != "advise":
            fails += 1
            print(f"FAIL  expected=advise got={got}  tail -n 20 on a 1.2MB file")

        got, _, _ = pg.classify(f"head -5 {small}", cwd=d)
        if got != "allow":
            fails += 1
            print(f"FAIL  expected=allow  got={got}  head -5 on a tiny file")

    fails += e2e()

    total = len(CASES) + 11
    if fails:
        print(f"\n{fails} FAILED")
        return 1
    print(f"{total}/{total} passed")
    return 0


def _run_hook(cmd: str, script: str = "probe-guard.py") -> tuple[int, str, str]:
    import json
    import subprocess

    p = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps({"tool_name": "Bash", "cwd": str(HOOKS),
                          "tool_input": {"command": cmd}}),
        text=True,
        capture_output=True,
    )
    return p.returncode, p.stdout, p.stderr


def e2e() -> int:
    """Driven exactly as Claude Code drives the hook.

    block  -> exit 2, stderr (the only model-visible blocking channel)
    advise -> exit 0, stdout JSON hookSpecificOutput.additionalContext
              (exit-1 stderr is USER-ONLY; verified live. The nudge must reach
              the model or it is decoration.)
    allow  -> exit 0, no stdout, no stderr
    """
    import json as _json

    fails = 0
    # (cmd, want_rc, want_channel)  channel: "block" | "advise" | "silent"
    checks = [
        ('ssh homeserver "docker stats --no-stream"', 2, "block"),
        ("ssh homeserver \"docker stats --no-stream --format '{{.MemUsage}}'\"", 0, "silent"),
        (
            "ssh homeserver \"docker exec w sh -c 'tail -c 2000 /var/log/app/alerts.json'\"",
            0,
            "advise",
        ),
        ("git status --short", 0, "silent"),
    ]
    for cmd, want_rc, chan in checks:
        rc, out, err = _run_hook(cmd)
        if rc != want_rc:
            fails += 1
            print(f"FAIL  e2e rc: expected {want_rc} got {rc}  {cmd}")
        if chan == "block" and "BLOCKED" not in err:
            fails += 1
            print(f"FAIL  e2e block: stderr lacks BLOCKED  {cmd}")
        elif chan == "advise":
            try:
                ctx = _json.loads(out)["hookSpecificOutput"]["additionalContext"]
            except Exception as exc:
                fails += 1
                print(f"FAIL  e2e advise: stdout not valid additionalContext JSON ({exc}) {out!r}")
            else:
                if "probe-guard" not in ctx:
                    fails += 1
                    print("FAIL  e2e advise: note does not identify probe-guard")
            if "permissionDecision" in out:
                fails += 1
                print("FAIL  advisory must NEVER emit permissionDecision — it bypasses the permission prompt")
        elif chan == "silent" and (out.strip() or err.strip()):
            fails += 1
            print(f"FAIL  e2e allow must be silent: out={out!r} err={err!r}")

    # PROSE THAT MENTIONS A PROBE IS NOT A PROBE.
    # This hook's own commit message quotes `top -bn1` and `tail -c 2000` while
    # explaining why not to run them — and the hook blocked the commit. Pinned.
    prose_cases = [
        ("git commit -q -F - <<'EOF'\nexplains why `top -bn1` is wrong\nand `tail -c 2000 f`\nEOF", 0),
        ("git commit -m 'fix: stop using docker stats --no-stream'", 0),
        ("git commit -m \"note: top -bn1 is meaningless\"", 0),
        # ...but a real probe OUTSIDE the heredoc still gets caught
        ("git commit -F - <<'EOF'\nprose\nEOF\ntop -bn1", 2),
    ]
    for cmd, want in prose_cases:
        rc, _out, _err = _run_hook(cmd)
        if rc != want:
            fails += 1
            print(f"FAIL  prose elision: expected rc={want} got {rc}  {cmd[:60]!r}")

    # the guard must actually be registered, or none of this runs
    conf = (HOOKS / "bash-guard.conf").read_text()
    if "probe-guard" not in conf:
        fails += 1
        print("FAIL  probe-guard not listed in bash-guard.conf")

    # dispatcher must be able to import it
    import importlib.util as iu

    try:
        s = iu.spec_from_file_location("pg2", HOOKS / "probe-guard.py")
        m = iu.module_from_spec(s)
        s.loader.exec_module(m)
        assert callable(m.main)
    except Exception as exc:
        fails += 1
        print(f"FAIL  dispatcher cannot load probe-guard: {exc}")

    return fails


if __name__ == "__main__":
    sys.exit(main())
