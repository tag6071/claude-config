#!/usr/bin/python3
"""
PreToolUse:Bash guard — evidence quality of shell probes.

Two failures this exists to stop, both drawn from a real infra-audit session
where confident numbers were derived from insufficient output:

  1. "The message broker burns 174% CPU permanently."  Came from the FIRST sample of
     `docker stats --no-stream`. CPU% is a RATE — it needs two counter reads.
     Three clean samples put the real figure at ~1.2%.

  2. "SIEM is just PAM login noise."  Came from `tail -c 2000` of a 5.7 MB
     alerts file, generalized to the whole distribution. The real distribution
     was thousands of integrity-check events plus live file-integrity hits.

Design notes, each learned the hard way:

  * A GAUGE is fine on one sample; only a RATE is not. `docker stats
    --format '{{.MemUsage}}'` is correct and must NOT be blocked — an earlier
    draft of this guard blocked it, which is exactly how a guard teaches you to
    disable it. Only a CPU% request blocks.

  * `iostat`/`vmstat`/`mpstat`/`sar` with no interval print a LABELED
    since-boot total, which is sometimes precisely what you want. Advise, never
    block.

  * The escape hatch must not be one the model can type. The multi-sample
    allowance is STRUCTURAL — a real `for … do` / `while … do` construct AND a
    `sleep` — so a trailing `# sleep` comment does not defeat it. The env bypass
    is read from the HOOK's environment (like block-secrets.py), so an inline
    `VAR=1 cmd` prefix never reaches this process.

  * head/tail are judged by whether they carry a FILE ARGUMENT, not by what
    follows in the pipeline. `tail -c 2000 f | sort | uniq -c` is still a peek of
    2000 bytes — aggregating a truncated input does not un-truncate it. Whereas
    `grep -o X f | sort | uniq -c | head -20` has a bare `head` reading stdin,
    which is display truncation and harmless.

Exit: 0 allow · 0 + JSON advise (command RUNS, note reaches the model) · 2 block.

ADVISORY CHANNEL — determined by experiment, not assumption. A PreToolUse hook
exiting 1 shows stderr to the USER ONLY; the model never sees it, so the nudge is
worthless (verified live, and confirmed in the hooks reference). The documented
model-visible channel is `hookSpecificOutput.additionalContext` on stdout with
exit 0 — it lands next to the tool result.

Deliberately NOT using `permissionDecision: "allow"`: that auto-approves the tool
call and bypasses the user's permission prompt. A guard must never quietly widen
permissions as a side effect of warning about statistics.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BYPASS = "CLAUDE_ALLOW_SINGLE_SAMPLE"

# Prose that MENTIONS a probe is not a probe: this hook's own commit message
# quoted `top -bn1` and the hook blocked it. Shared elision, see hook_common.
# sys.path insert: guarantee the import resolves however the guard is loaded.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import elide_prose

# --- structural multi-sample detection (not defeatable by a `# sleep` comment) ---
# NB: `for i in 1 2 3; do` contains a semicolon before `do`, so this must span
# `;` — an earlier `[^;]*?` version silently failed every real loop.
_LOOP = re.compile(r"\bfor\s+\w+\s+in\b[^\n]*?\bdo\b|\bwhile\b[^\n]*?\bdo\b")
_SLEEP = re.compile(r"\bsleep\s+[\d.]")
_COMMENT = re.compile(r"(?m)(?:^|\s)#.*$")

# --- docker stats ---
_DOCKER_STATS = re.compile(r"\bdocker\s+stats\b")
_NO_STREAM = re.compile(r"--no-stream\b")
_FORMAT = re.compile(r"--format(?:=|\s+)(?:(['\"])(.*?)\1|(\S+))")

# --- top ---
_TOP = re.compile(r"\btop\b")
_TOP_BN1 = re.compile(r"-bn\s*1\b")
_TOP_B = re.compile(r"-b\b")
_TOP_N1 = re.compile(r"-n\s*1\b")

# --- byte slicing / line peeking ---
_HEADTAIL = re.compile(r"\b(head|tail)\b([^|;&\n]*)")
_BYTES = re.compile(r"(?:-c\s*|--bytes[=\s])(\d+)")
_LINES = re.compile(r"(?:-n\s*|--lines[=\s])(\d+)")
_SED_RANGE = re.compile(r"\bsed\b[^|;&\n]*-n[^|;&\n]*?\b\d+\s*,\s*\d+\s*p")

# --- since-boot samplers ---
_SAMPLER = re.compile(r"\b(iostat|vmstat|mpstat|sar)\b([^|;&\n]*)")

BYTE_PEEK_MIN = 1000  # `head -c 512` sniffing magic bytes is legitimate.
BIG_FILE = 1_000_000  # bytes; below this a small -n peek is not a distribution claim
LINE_PEEK_MAX = 1000

DOCKER_FIX = (
    "for i in 1 2 3; do docker stats --no-stream "
    "--format '{{.Name}} {{.CPUPerc}}'; sleep 2; done   # discard sample 1"
)
TOP_FIX = "top -bn2 ... | tail -n +8   # use the SECOND iteration"
PEEK_FIX = "grep -o '<field>' FILE | sort | uniq -c | sort -rn"


def _is_multi_sample(cmd: str) -> bool:
    """A real loop construct AND a sleep. Both, or neither.

    Comments are stripped FIRST, so neither `# sleep` nor `# for i in 1 2 3; do`
    can forge the allowance. The threat model is not an attacker — it is the
    model itself, twelve turns deep, wanting the number.
    """
    live = _COMMENT.sub("", cmd)
    return bool(_LOOP.search(live)) and bool(_SLEEP.search(live))


def _format_value(cmd: str) -> str | None:
    m = _FORMAT.search(cmd)
    if not m:
        return None
    return m.group(2) if m.group(2) is not None else m.group(3)


def _has_file_arg(args: str) -> bool:
    """True if this head/tail invocation names a file rather than reading stdin."""
    toks = args.replace("'", " ").replace('"', " ").split()
    skip_next = False
    for tok in toks:
        if skip_next:
            skip_next = False
            continue
        if tok in ("-c", "-n", "--bytes", "--lines"):
            skip_next = True
            continue
        if tok.startswith("-"):
            continue
        if tok.isdigit():  # bare number: `tail -20` style
            continue
        return True
    return False


def _file_size(token: str, cwd: Path) -> int | None:
    try:
        p = Path(token)
        p = p if p.is_absolute() else cwd / p
        return p.stat().st_size if p.is_file() else None
    except Exception:
        return None


def _first_file_token(args: str) -> str | None:
    toks = args.replace("'", " ").replace('"', " ").split()
    skip_next = False
    for tok in toks:
        if skip_next:
            skip_next = False
            continue
        if tok in ("-c", "-n", "--bytes", "--lines"):
            skip_next = True
            continue
        if tok.startswith("-") or tok.isdigit():
            continue
        return tok
    return None


def _has_interval(args: str) -> bool:
    return any(t.isdigit() for t in args.split())


def classify(cmd: str, cwd: str | None = None) -> tuple[str, str, str]:
    """Return (verdict, reason, fix). verdict in {block, advise, allow}."""
    base = Path(cwd) if cwd else Path.cwd()

    multi = _is_multi_sample(cmd)

    # ---- BLOCK: single read of a rate counter ----
    if _DOCKER_STATS.search(cmd) and _NO_STREAM.search(cmd) and not multi:
        fmt = _format_value(cmd)
        if fmt is None:
            return (
                "block",
                "`docker stats --no-stream` with no --format prints the default table, "
                "which includes CPU %. CPU% is a RATE: one sample cannot produce it "
                "(precpu_stats may be zero or incomplete).",
                DOCKER_FIX,
            )
        if "cpu" in fmt.lower():
            return (
                "block",
                f"`docker stats --no-stream --format {fmt!r}` asks for CPU%. That is a "
                "RATE: one sample cannot produce it.",
                DOCKER_FIX,
            )
        # Memory / Net / Block / PIDs are GAUGES — one sample is correct.

    if _TOP.search(cmd) and not multi:
        if _TOP_BN1.search(cmd) or (_TOP_B.search(cmd) and _TOP_N1.search(cmd)):
            return (
                "block",
                "`top -bn1` prints a %CPU computed against no prior sample. "
                "The number is meaningless, not merely coarse.",
                TOP_FIX,
            )

    # ---- ADVISE: a peek is not a distribution ----
    for m in _HEADTAIL.finditer(cmd):
        args = m.group(2)
        if not _has_file_arg(args):
            continue  # bare `| head -20` = display truncation, harmless
        bm = _BYTES.search(args)
        if bm and int(bm.group(1)) >= BYTE_PEEK_MIN:
            return (
                "advise",
                f"byte-sliced {bm.group(1)} B out of a file. Byte-slicing is ALWAYS "
                "sampling — nobody -c's a file to read it.",
                PEEK_FIX,
            )
        lm = _LINES.search(args)
        if lm and int(lm.group(1)) <= LINE_PEEK_MAX:
            tok = _first_file_token(args)
            size = _file_size(tok, base) if tok else None
            if size and size >= BIG_FILE:
                return (
                    "advise",
                    f"read {lm.group(1)} lines of a {size / 1e6:.1f} MB file.",
                    PEEK_FIX,
                )

    if _SED_RANGE.search(cmd):
        return (
            "advise",
            "`sed -n 'N,Mp'` slices a line range. That is a peek, not a distribution — "
            "and it is the form that once dumped a private key into a transcript.",
            PEEK_FIX,
        )

    for m in _SAMPLER.finditer(cmd):
        if not _has_interval(m.group(2)):
            tool = m.group(1)
            return (
                "advise",
                f"`{tool}` with no interval prints a since-boot TOTAL, not a current rate. "
                "Fine if a total is what you want; wrong if you are about to quote a rate.",
                f"{tool} 1 2   # use the LAST sample",
            )

    return ("allow", "", "")


def main() -> int:
    if os.environ.get(BYPASS) == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    cmd = tool_input.get("command") or ""
    if not cmd:
        return 0

    try:
        verdict, reason, fix = classify(elide_prose(cmd), payload.get("cwd") or os.getcwd())
    except Exception:  # fail open, LOUDLY — never wedge Bash
        import traceback

        traceback.print_exc(file=sys.stderr)
        return 0

    if verdict == "block":
        sys.stderr.write(
            f"BLOCKED by ~/.claude/hooks/probe-guard.py — single-sample rate probe.\n\n"
            f"  {reason}\n\n"
            f"  instead: {fix}\n\n"
            f"  offending: {cmd[:200]}\n"
            f"  override (user-set in their own shell, not inline): {BYPASS}=1\n"
        )
        return 2

    if verdict == "advise":
        # Exit 0 + additionalContext: the command RUNS and the note lands next to
        # the tool result, where the model actually reads it. stderr on exit 1 is
        # user-only and would be a nudge nobody sees.
        note = (
            f"⚠ probe-guard: {reason}\n"
            "This is a PEEK, not a distribution. Do NOT generalize from this output "
            "about what the file or counter mostly contains — the sample is not the "
            f"population.\nFor real counts, re-run over the WHOLE file: {fix}"
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": note,
                    }
                }
            )
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
