#!/usr/bin/env python3
"""terse-gate.py — Stop hook. BLOCKS a turn whose final message is an essay.

WHY THIS EXISTS
  `outputStyle: terse` was already on globally and the model still shipped
  multi-paragraph explanations nobody asked for. Prompt-level style is a
  suggestion that decays over a long session; a hook is not. Every other
  habit the user wanted gone (prod writes, secrets, doc sprawl, lazy
  handoffs) is enforced mechanically. Verbosity had no enforcement at all.

  It also counterweights persist-gate.py, which blocks a stop until the model
  proves it exhausted self-serve options — pressure that reliably produces
  "here is everything I checked and why" prose. persist-gate polices whether
  work happened; terse-gate polices how much talking wraps it.

WHAT IT MEASURES (on the LAST assistant text block only)
  Fenced/inline code is stripped first — code and command output are not
  chatter, and the user reads them directly.
  * prose words   — words on lines that are NOT bullets / table rows /
                    headings / quotes. Paragraphs are the failure mode;
                    tables and bullets are the requested shape, so they are
                    counted at a discount (total budget only).
  * total words   — everything left after stripping code.
  * preamble      — "Let me...", "I'll now...", "Here's the picture" openers.
  * postamble     — "let me know if", "want me to", "hope that helps" closers.

RELEASE VALVES (deliberate, narrow)
  * a line starting `DEPTH:` — the user asked for depth, or a real decision
    genuinely needs the room. Naming it costs one line and is auditable.
  * stop_hook_active — at most ONE correction per turn, so a rewrite that is
    still slightly long cannot trap the session in a loop.

Contract: allow -> exit 0 silently. block -> print JSON, exit 0.
Fails OPEN on any parse error — a broken transcript must never wedge a turn.

Self-test: python3 terse-gate.py --selftest
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

# Budgets. Tuned so a normal terse answer (lead line + a table + one caveat)
# passes untouched, while the transcript that prompted this hook — several
# explanatory paragraphs plus a recap — does not.
PROSE_WORD_MAX = 120   # words in paragraph-shaped lines
TOTAL_WORD_MAX = 350   # words in the whole message, code stripped

DEPTH_MARKER = re.compile(r"^\s*DEPTH:", re.IGNORECASE | re.MULTILINE)

# Openers that announce work instead of doing it.
PREAMBLE = [
    r"^\s*(ok(ay)?[,.]?\s*)?let me\b",
    r"^\s*i'?ll (now|go ahead|start by)\b",
    r"^\s*(here'?s|here is) (the picture|what|the plan|the state|the situation)\b",
    r"^\s*(great|good) question\b",
    r"^\s*(first|before) (i|we) (do|start|begin)\b",
    r"^\s*(straight|honest) (status|answer)\b",
    r"^\s*you['’]?re right\s*[,;:—–-]",
]

# Closers that pad the end: recaps, offers, reassurance.
POSTAMBLE = [
    r"\blet me know if\b",
    r"\bwant me to\b",
    r"\bwould you like me to\b",
    r"\bhope (that|this) helps\b",
    r"\bto (summari[sz]e|recap)\b",
    r"\bin summary\b",
    r"\bfeel free to\b",
    r"\bshould work now\b",
]

STRUCTURED = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\||#{1,6}\s|>|\s*$)")


def _read_stdin_json() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def _await_final_flush(transcript_path: str, timeout: float = 1.5) -> None:
    """Wait for the turn's FINAL assistant message to reach the transcript.

    The Stop hook can fire before that last message is written. Reading the file
    then yields the PREVIOUS assistant text — which, mid-turn, is usually a
    one-line "about to run X" narration — so the gate judges a message the user
    never saw as final, and its complaint makes no sense against what is on
    screen. Observed twice in one session: terse-gate flagged a
    "Let me check the actual Disk Utility…" preamble, and persist-gate flagged a
    "say go" handoff, both from the prior message while the real final answer had
    already been delivered. Confirmed by replaying the hook's own extractor over
    the transcript afterwards: the matched text sat at message #40 of 41.

    Poll until an assistant record carrying a text block is the file's tail.
    Fails OPEN on timeout or any error — a gate must never wedge a turn.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            tail = None
            with open(transcript_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        tail = line
            obj = json.loads(tail) if tail else {}
            if obj.get("type") == "assistant":
                content = (obj.get("message") or {}).get("content")
                if isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip()
                    for b in content
                ):
                    return
        except Exception:
            return
        time.sleep(0.05)


def _last_assistant_text(transcript_path: str) -> str:
    """Last assistant TEXT block in the transcript (tool calls ignored)."""
    if not transcript_path or not os.path.exists(transcript_path):
        return ""
    _await_final_flush(transcript_path)
    last = ""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message") or {}
                if msg.get("role") != "assistant":
                    continue
                content = msg.get("content")
                parts = []
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                text = "\n".join(p for p in parts if p)
                if text.strip():
                    last = text
    except Exception:
        return ""
    return last


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def _match_any(patterns: list[str], text: str) -> str:
    for p in patterns:
        if re.search(p, text, re.IGNORECASE | re.MULTILINE):
            return p
    return ""


def evaluate(text: str) -> tuple[bool, str]:
    """Return (should_block, reason)."""
    if not text.strip():
        return False, ""
    if DEPTH_MARKER.search(text):
        return False, ""

    body = _strip_code(text)
    lines = body.splitlines()
    prose_lines = [ln for ln in lines if ln.strip() and not STRUCTURED.match(ln)]
    prose_words = sum(len(ln.split()) for ln in prose_lines)
    total_words = len(body.split())

    # Openers/closers are judged on the edges only — quoting "let me know if"
    # mid-answer while explaining something is not the same as ending on it.
    head = "\n".join(prose_lines[:2])
    tail = "\n".join(prose_lines[-2:])

    if prose_words > PROSE_WORD_MAX:
        return True, _reason(
            f"{prose_words} words of paragraph prose (budget {PROSE_WORD_MAX})",
            "Cut it to the result + at most one caveat clause. Move anything "
            "enumerable into a table or bullets.",
        )
    if total_words > TOTAL_WORD_MAX:
        return True, _reason(
            f"{total_words} words total (budget {TOTAL_WORD_MAX})",
            "Even as bullets this is a wall. Keep what changes the user's next "
            "action; delete the rest.",
        )
    if (sig := _match_any(PREAMBLE, head)):
        return True, _reason(
            f"opens with preamble (matched {sig!r})",
            "Delete the opener. First line = the result, the change, or the "
            "direct answer. Never an announcement of what you are about to do.",
        )
    if (sig := _match_any(POSTAMBLE, tail)):
        return True, _reason(
            f"ends with postamble (matched {sig!r})",
            "Delete the closer. When the work is done, stop — no recap, no "
            "offer of next steps the user did not ask for.",
        )
    return False, ""


def _reason(what: str, fix: str) -> str:
    return (
        "TERSE GATE blocked stop.\n\n"
        f"Your final message: {what}.\n\n"
        f"{fix}\n\n"
        "The user chose terse mode because talk-over-action wastes their time. "
        "Tool output and diffs speak for themselves — do not narrate them.\n\n"
        "Rewrite the message shorter and stop. If depth was genuinely asked "
        "for, or a real decision needs the room, add a line starting 'DEPTH:' "
        "naming why — that releases the gate.\n\n"
        "Bypass (user only): export CLAUDE_SKIP_TERSE_GATE=1"
    )


def _selftest() -> int:
    cases = [
        # (text, expect_block)
        ("Fixed. `foo.py:12` had the wrong key.", False),
        ("Done — tests green.\n\n| host | state |\n|---|---|\n| homeserver | up |", False),
        ("Let me check the config first.", True),
        ("Deleted the stale lease.\n\nLet me know if you want the other one too.", True),
        ("word " * 130, True),
        ("DEPTH: user asked for the full tradeoff writeup.\n" + "word " * 200, False),
        ("Here's the picture — probed live, not guessed.", True),
        # code is not chatter: a long fenced block alone must pass
        ("Applied:\n\n```\n" + "\n".join(f"line {i}" for i in range(200)) + "\n```", False),
        # bullets are the requested shape, not a paragraph
        ("Three gaps:\n" + "\n".join(f"- gap {i} explained briefly here" for i in range(8)), False),
        ("You're right — I did zero digging this turn.", True),
    ]
    bad = 0
    for text, expect in cases:
        got, _ = evaluate(text)
        if got != expect:
            bad += 1
            print(f"FAIL expect_block={expect} got={got}: {text[:60]!r}")
    print("terse-gate selftest:", "PASS" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if os.environ.get("CLAUDE_SKIP_TERSE_GATE"):
        return 0
    data = _read_stdin_json()
    # One correction per turn — a still-slightly-long rewrite must not loop.
    if data.get("stop_hook_active"):
        return 0
    text = _last_assistant_text(data.get("transcript_path", ""))
    block, reason = evaluate(text)
    if block:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
