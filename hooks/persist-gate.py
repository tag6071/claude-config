#!/usr/bin/env python3
"""
Stop hook: PERSIST GATE (anti-capitulation).  GENERAL, app-agnostic.

Kills two recurring failures:
  (1) the model retreats to handing a RUNNABLE step back to the user ("run
      this", "you run it", "tell me when", "go click", "give it a try")
      instead of doing it itself — or invents a FAKE "it's a secret" reason to
      offload a command whose secret pipes straight through a tool it never sees;
  (2) the model PUNTS A DECISION / ASKS A QUESTION it could have answered by
      searching the docs, searching online, reading the codebase's own
      conventions, or just trying it ("should I…", "which do you want…", "let
      me know…"). This is the laziness the user is angriest about.

The user's standing rule: "A manual step handed to the user is a defect," and
its sharper sibling: "Exhaust every self-serve option before you hand ME
anything." Soft rules got rationalized past. This hook gives them TEETH.

DETECTION (on the last assistant message)
-----------------------------------------
HANDOFF signature  -> frames a step for the USER to perform ("run this", "you
  run", "paste the output", "tell me when", "go click", "give it a try", ...).
QUESTION signature -> punts a decision/question to the user ("should I", "do you
  want me to", "which …", "let me know", "your call", "ok to proceed?", ...).

RELEASE (structural — the hard ones can't be typed past):
  1. No handoff/question signature -> the model just did work -> allow.
  2. EXHAUSTION GATE: a handoff OR question with ZERO investigative tool calls
     THIS turn (WebSearch/WebFetch/Grep/Glob/Read/Bash/Task/…) is BLOCKED with
     no escape — not even an IRREDUCIBLE line. You cannot know a step is
     irreducible until you've searched docs, searched online, read the codebase
     conventions, and tried it. Evidence is counted from the transcript, so the
     model cannot satisfy it by TYPING — only by actually investigating.
  3. After investigating, an explicit `IRREDUCIBLE:` line naming a GENUINELY
     irreducible reason releases a handoff: physical action (cable/button/power)
     / a genuine user DECISION no research could settle / a secret the user must
     TYPE (vault-set / paste), which the model must not see.
  4. CLAUDE_SKIP_PERSIST_GATE=1 in env -> USER-only bypass (single shell) for a
     genuine misfire. Read from the HOOK's env, not model-typeable in a message.

ANTI-GAMING (the fake-secret loophole)
--------------------------------------
If the handed-over command pipes a vault READ (vault-view / vault-show /
vault-get / vault-cat / vault-decrypt, e.g. `$(... vault-view ...)`), the
"secret" justification is VOID: running it exposes nothing to the model, so
the model MUST run it. An `IRREDUCIBLE:` line citing "secret" is rejected in
that case. (vault-SET / vault-edit / paste are the user TYPING a value — that
IS irreducible and is allowed.)

Hook protocol: reads JSON on stdin, writes JSON on stdout.
  allow -> exit 0, no output
  block -> print {"decision":"block","reason":"..."} , exit 0

Self-test:  python3 persist-gate.py --selftest
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

BYPASS_ENV = "CLAUDE_SKIP_PERSIST_GATE"

# The message frames a runnable / manual step for the USER. App-agnostic.
# NOTE: scanned against PROSE with code blocks + quoted spans stripped (see
# _strip_noise) so that DISCUSSING a handoff ("so I run it", quoting the gate)
# does not trip the gate — only an actual directive to the user does.
HANDOFF_PATTERNS = [
    r"\b(can|could|would|please)\s+(you\s+)?(run|paste|check|click|tap|type|open)\b",
    # imperative "Run this/it/the command" — only at a sentence/line start, so
    # first-person "so I run it" / "the value never reaches me, so I run it" is NOT a match
    r"(?:^|[.!?:•\-\n])\s*run\s+(this|these|those|the\s+following|it|them|the\s+command)\b",
    r"\byou\s+(can\s+|should\s+|just\s+)?run\s+(this|these|the|that|it|them)\b",
    r"\bgo\s+run\b",
    # "Run: <cmd>" as a DIRECTIVE — anchored to the start of a line/bullet so a
    # noun phrase ending in "run" used as a label ("Previous cloud run: …",
    # "**Real run:** finished clean") is not a handoff. Caught in practice: a
    # status report of work already DONE was blocked by the unanchored form.
    # The bullet marker is anchored to the line start too: a bare `-` alternative
    # matched the hyphen inside "dry-run: only timestamps differ" (a table cell
    # reporting a finished check).
    r"^\s*(?:[•\-*]\s*)?(?:\*\*)?run\s*:",
    r"\brun\s+(the\s+)?(command|cmd|following|two|three|playbook|one[- ]liner)s?\b",
    r"\bpaste\s+(the\s+)?(output|result|error|it)\b",
    r"\b(and|then)\s+(tell|let)\s+me\b",
    r"\b(tell|let)\s+me\s+(when|the\s+output|what|if)\b",
    r"\bsay\s+(next|done|when\s+you|ready|go)\b",
    r"\bgo\s+click\b",
    r"\bgo\s+verify\b",
    # "go test" needs a handoff OBJECT to count. Bare `go test` is the Go
    # toolchain command, so REPORTING work already done ("verified: go test,
    # web gate, 57/57 e2e") was blocked as if it were a handoff. Caught
    # Same class as the anchored "run:" fix above.
    r"\bgo\s+test\s+(it|this|that|them|yourself|manually|in)\b",
    r"\bverify\s+in\s+your\s+browser\b",
    r"\bgive\s+it\s+a\s+try\b",
    r"\bshould\s+work\s+now\b",
    # "...plays its sound when you click it" DESCRIBES a feature; only a bare directive is a handoff.
    # Caught in practice (click-to-hear feature report blocked as a handoff).
    r"(?<!\bwhen\s)(?<!\bwhenever\s)(?<!\bif\s)(?<!\bonce\s)(?<!\bas\s)\byou\s+(drive|navigate|handle|do|click|tap)\s+(the|these|those|it)\b",
    r"\bin\s+(the\s+)?(app|settings)[,]?\s+(go\s+to|navigate|open|tap|click)\b",
    r"\bfocus\s+the\s+\w+\s+field[,]?\s+(then\s+)?run\b",
    r"\bnavigate\s+to\b.*\bthen\b",
    r"\bin\s+\w+\s*(→|->|>)\s*\w+",   # "in SomeApp -> Settings -> ..." breadcrumb to the user
]

# The model punting a DECISION or a QUESTION back to the user instead of
# deciding/finding out itself. This is the "you start asking me stupid questions
# you could have researched" failure — the user is MORE furious about this than
# about runnable handoffs. App-agnostic. Scanned on PROSE (code/quotes stripped).
QUESTION_PATTERNS = [
    r"\bshould\s+i\b",
    r"\bdo\s+you\s+want\s+(me\s+)?(to|it)\b",
    r"\bwould\s+you\s+(like|prefer|rather)\b",
    r"\bwhich\s+(one|option|approach|way|do\s+you)\b",
    r"\b(let|tell)\s+me\s+know\b",
    r"\bwhat('?s| is| do you)\b.*\?",
    r"\byour\s+call\b",
    r"\bup\s+to\s+you\b",
    r"\b(want|shall)\s+(me\s+to|i)\b",
    r"\bhow\s+(do|would)\s+you\s+want\b",
    r"\bcan\s+you\s+(confirm|clarify|tell\s+me|decide|choose)\b",
    r"\bplease\s+(confirm|clarify|advise|decide|choose|specify)\b",
    r"\bproceed\?\s*$",
    r"\bok(ay)?\s+to\s+(proceed|continue|go\s+ahead)\b",
]

# Tool calls that PROVE self-serve effort this turn: searching, reading, probing,
# delegating a search. The exhaustion release is STRUCTURAL — evidence in the
# transcript, not a phrase the model types. This is the teeth the user asked for:
# "search the docs, search online, read the codebase conventions, TRY it" — a
# handoff/question with ZERO of these since the last user turn is auto-blocked.
INVESTIGATIVE_TOOLS = {
    "WebSearch", "WebFetch", "Grep", "Glob", "Read", "Bash", "Task", "Agent",
    "LSP", "NotebookRead", "ToolSearch", "ListMcpResourcesTool",
    "ReadMcpResourceTool", "mcp__db-mcp__db_select", "mcp__db-mcp__db_describe",
}
# Driving a browser or the desktop IS "try it yourself". Without this, two real
# attempts the auto-mode classifier denied counted as zero investigation and the
# gate demanded docs searches that cannot lift a permission denial.
ATTEMPT_PREFIXES = ("mcp__claude-in-chrome__", "mcp__computer-use__", "mcp__Claude_Browser__")

# A vault READ piped into a command -> the secret never reaches the model.
# Therefore the model CAN run the handed-over command itself.
VAULT_READ_PIPE = re.compile(
    r"vault[-_ ]?(view|show|get|cat|decrypt|read)\b", re.IGNORECASE
)

# The explicit, deliberate release marker. Must be on its own line.
IRREDUCIBLE_MARKER = re.compile(r"^\s*IRREDUCIBLE:", re.IGNORECASE | re.MULTILINE)

# Words that, on the IRREDUCIBLE line, claim a secret reason.
SECRET_CLAIM = re.compile(
    r"\b(secret|password|credential|vault|token|key)\b", re.IGNORECASE
)


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
    screen. Worse here than in terse-gate: this gate also reports "ZERO
    investigation this turn", because the tool calls it is counting have not
    landed either.

    Observed three times in one session. Proven by replaying this
    hook's own extractor over the transcript afterwards: the matched 'say go'
    text sat at message #40 of 41 while the real final message was already
    delivered.

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


def _investigations_since_last_user(transcript_path: str) -> int:
    """Count investigative tool calls since the last USER (human) message.

    Walks the transcript, resets the counter at every human turn, and tallies
    assistant tool_use blocks whose tool name is in INVESTIGATIVE_TOOLS. The
    return value is the model's PROOF of self-serve effort THIS turn. Zero means
    it handed off / asked without searching, reading, or trying anything — the
    exact laziness the gate now refuses. On any parse failure returns a large
    number (fail-OPEN on evidence) so a broken transcript never traps the model
    in the harsher exhaustion branch; the handoff/question branch still applies.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return 999
    count = 0
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
                typ = obj.get("type")
                if typ == "user":
                    msg = obj.get("message") or {}
                    content = msg.get("content")
                    # A real human turn resets the counter; tool_result-only
                    # "user" frames (tool output plumbing) do NOT — they carry
                    # no human text and must not wipe the evidence tally.
                    is_human = isinstance(content, str) or (
                        isinstance(content, list)
                        and any(
                            isinstance(b, dict) and b.get("type") == "text"
                            for b in content
                        )
                    )
                    if is_human:
                        count = 0
                    continue
                if typ != "assistant":
                    continue
                msg = obj.get("message") or {}
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and (block.get("name") in INVESTIGATIVE_TOOLS
                             or str(block.get("name", "")).startswith(ATTEMPT_PREFIXES))
                    ):
                        count += 1
    except Exception:
        return 999
    return count


def _match_any(patterns: list[str], text: str) -> str:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE | re.MULTILINE):
            return pat
    return ""


def _strip_noise(text: str) -> str:
    """Remove code + quoted spans so DISCUSSING a handoff doesn't read as one.

    Fenced/inline code and short quoted spans are where example commands and
    meta-quotes of the gate's own wording live ("you run it", `$(rr vault-view)`).
    Stripping them leaves only the model's own prose directives to scan.
    """
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)   # fenced code
    text = re.sub(r"`[^`]*`", " ", text)                       # inline code
    text = re.sub(r"'[^']{0,160}'", " ", text)                 # 'single-quoted'
    text = re.sub(r'"[^"]{0,160}"', " ", text)                 # "double-quoted"
    return text


def evaluate(text: str, investigations: int = 999) -> tuple[bool, str]:
    """Return (should_block, reason).

    `investigations` = count of investigative tool calls THIS turn (see
    _investigations_since_last_user). It defaults high so pure-prose callers
    (the selftest's phrasing cases) exercise only the handoff/question logic.
    """
    if not text.strip():
        return False, ""

    # Handoff/question are judged on PROSE (code/quotes stripped); vault-pipe +
    # marker are judged on FULL text (the command lives in code we stripped).
    prose = _strip_noise(text)
    handoff = _match_any(HANDOFF_PATTERNS, prose)
    question = _match_any(QUESTION_PATTERNS, prose)
    if not handoff and not question:
        return False, ""  # did the work / only discussed it -> fine to stop

    signal = handoff or question
    is_question = bool(question) and not handoff

    vault_pipe = bool(VAULT_READ_PIPE.search(text))
    has_marker = bool(IRREDUCIBLE_MARKER.search(text))

    # The fake-secret loophole: a vault READ pipe means the model never sees
    # the value -> it MUST run the command. Blocks unconditionally.
    if vault_pipe:
        return True, _reason(signal, kind="vault", is_question=False)

    # EXHAUSTION GATE (the hard one, no typed escape): if the model hands off OR
    # asks a question with ZERO investigative tool calls this turn, it did not
    # search the docs / search online / read the codebase / try it. An
    # `IRREDUCIBLE:` line does NOT release this — you cannot declare a step
    # irreducible without first investigating enough to KNOW it is. Only real
    # tool calls (or the user's env bypass) clear it.
    if investigations == 0:
        return True, _reason(signal, kind="exhaust", is_question=is_question)

    # Investigated, and it's a genuine irreducible step, explicitly declared.
    if has_marker:
        return False, ""

    return True, _reason(signal, kind="handoff", is_question=is_question)


def _reason(signal: str, *, kind: str, is_question: bool) -> str:
    verb = (
        "punts a DECISION / asks the user a question"
        if is_question
        else "hands a runnable step back to the user"
    )
    head = (
        "PERSIST GATE blocked stop.\n\n"
        f"Your last message {verb} instead of doing/finding out yourself "
        f"(matched signal: {signal!r}).\n\n"
    )

    if kind == "vault":
        head += (
            "AND the command you handed over pipes a VAULT READ "
            "(vault-view/show/get). That value flows vault -> tool -> target; "
            "YOU NEVER SEE IT. So 'it's a secret, you run it' is FALSE — run it "
            "yourself. This exact fake-irreducible excuse is what the user is "
            "furious about. There is no security reason to offload a vault-pipe "
            "command.\n\n"
        )

    if kind == "exhaust":
        # The hard branch: no investigation happened this turn.
        return head + (
            "AND you did this with ZERO investigation this turn — no doc read, "
            "no web search, no codebase grep, no attempt. That is the exact "
            "laziness the user is furious about.\n\n"
            "You may NOT stop, and NO 'IRREDUCIBLE:' line saves you here — you "
            "cannot know a step is irreducible until you have EXHAUSTED the "
            "self-serve options. Before you hand ANYTHING back, actually do:\n"
            "  1. SEARCH THE OFFICIAL DOCS for this tool/API/app (WebFetch/WebSearch).\n"
            "  2. SEARCH ONLINE for how others automate/solve it (WebSearch).\n"
            "  3. READ THE CODEBASE'S OWN CONVENTIONS — grep for how it's already\n"
            "     done here (Grep/Glob/Read), the playbook, existing scripts.\n"
            "  4. TRY IT YOURSELF — run the command, drive the flow, probe the API,\n"
            "     find the headless flag / config path / CLI shim.\n"
            "Then DECIDE & SHIP a sensible default (working agreement #1). Only "
            "after all of that turns up genuinely nothing may a handoff even be "
            "considered — and then it needs a real IRREDUCIBLE reason below.\n\n"
            f"Emergency bypass (ONLY the user, only if this gate is truly wrong): "
            f"export {BYPASS_ENV}=1"
        )

    return head + (
        "The user's standing rule: 'A manual step handed to the user is a defect.'\n\n"
        "Do ONE of these, then you may stop:\n"
        "  (a) DO IT / DECIDE IT YOURSELF. Run the command, drive the UI recipe,\n"
        "      build the automation, or pick a sensible default and ship it.\n"
        "      Exhaust real options first: the device/app API or file format, a\n"
        "      CLI/script/uiautomator shim, a headless flag or config path, the\n"
        "      OFFICIAL DOCS, an ONLINE search for how others do it, and the\n"
        "      CODEBASE'S OWN CONVENTIONS. Almost every command or question you'd\n"
        "      hand the user, you can resolve yourself.\n\n"
        "  (b) JUSTIFY it as genuinely IRREDUCIBLE. Add a line starting\n"
        "      'IRREDUCIBLE:' naming exactly ONE of:\n"
        "        - a PHYSICAL action (cable, button, power),\n"
        "        - a genuine user DECISION that no research could settle,\n"
        "        - a secret the user must TYPE (vault-set / paste) and you must\n"
        "          not see  (NOT a vault-READ pipe — that one you run yourself).\n"
        "      If none is literally true, it is NOT irreducible — go to (a).\n\n"
        "Reflexively retreating to 'you run it' / 'which do you want?' is the\n"
        "pattern the user is tired of. Persist.\n\n"
        f"Emergency bypass (ONLY the user, only if this gate is truly wrong): "
        f"export {BYPASS_ENV}=1"
    )


def _selftest() -> int:
    cases = [
        # (text, expect_block)
        ("Done — import finished and the data is live. Verified on-device.", False),
        ("Email field is focused. Run this:\n`mytool login --password \"$(uv run rr vault-view secrets.yml)\"`\nSay next.", True),
        ("Focus the Email field, then run these two. Tell me when you're logged in.", True),
        ("In SomeApp → Settings → Backup, create a backup. Tell me when done.", True),
        ("Give it a try and let me know.", True),
        ("IRREDUCIBLE: press the physical pairing button on the device, then I continue.\nPlease press it now.", False),
        ("IRREDUCIBLE: you must TYPE the email into vault-set, I must not see it.\nRun: uv run rr vault-set app_email secrets.yml", False),
        # fake-secret loophole: vault READ pipe + claims secret -> still block
        ("IRREDUCIBLE: it's a secret password I can't see.\nRun: `mytool login --password \"$(rr vault-view secrets.yml)\"`", True),
        ("I refactored the parser and all tests pass.", False),
        # --- regression: META-DISCUSSION of the gate must NOT block (false positive fix) ---
        # the model EXPLAINING the gate, quoting its phrases + a vault example in code/quotes
        ("Done — the gate is live. When I hand you a runnable step the hook blocks it. "
         "The fake-secret excuse is dead: a `$(rr vault-view secrets.yml)` pipe is mine to run "
         "— the value never reaches me, so I run it. Real handoffs pass via an explicit "
         "IRREDUCIBLE line. Want the doc line added too?", False),
        # quoting the gate's own trigger wording in double-quotes
        ("This exact fake-irreducible excuse — \"it's a secret, you run it\" — is what the gate "
         "now rejects, because the value flows vault -> tool -> target and I never see it.", False),
        ("The pattern matched 'you run it / you click it'; that's the handoff I should avoid.", False),
        # --- regression: a hyphenated "-run:" noun is not a bullet "Run:" directive ---
        ("| Other synced files | checksum dry-run: only timestamps differ | ✅ |", False),
        ("Did a test-run: 57/57 pass.", False),
        ("- Run: make test", True),
        # --- regression: describing what happens "when you click it" is a feature, not a handoff ---
        ("Every item in the list plays its sound when you click it. All 51 tests pass.", False),
        ("Next, you click the Allow button and tell me when it's done.", True),
        ("• **Run:** make test", True),
    ]
    ok = True
    for text, expect in cases:
        # legacy phrasing cases: assume investigation happened (isolate handoff logic)
        block, _ = evaluate(text, investigations=5)
        status = "OK " if block == expect else "FAIL"
        if block != expect:
            ok = False
        print(f"  [{status}] expect_block={expect!s:5} got={block!s:5}  {text[:60]!r}")

    # (text, investigations, expect_block) — the new QUESTION + EXHAUSTION teeth
    inv_cases = [
        # asking a question WITHOUT investigating -> hard block
        ("Should I use Postgres or SQLite for this?", 0, True),
        ("Which approach do you want me to take?", 0, True),
        ("Let me know how you'd like to proceed.", 0, True),
        # same question AFTER investigating -> allowed (genuine decision surfaced)
        ("I checked the docs and both work; which do you prefer?", 5, True),
        # ^ still blocks: a bare preference punt should DECIDE&SHIP. Question always
        #   needs an IRREDUCIBLE line to pass. Confirm that:
        ("IRREDUCIBLE: genuine user DECISION.\nI researched both; which do you prefer?", 5, False),
        # a runnable handoff with zero investigation -> exhaustion block (marker can't save it)
        ("IRREDUCIBLE: press the physical button.\nGo run this now.", 0, True),
        # same physical handoff AFTER investigating -> allowed
        ("IRREDUCIBLE: press the physical pairing button.\nGo run this now.", 3, False),
        # pure work, no handoff/question, no investigation -> allow (nothing to gate)
        ("Refactored the parser; all tests pass.", 0, False),
    ]
    for text, inv, expect in inv_cases:
        block, _ = evaluate(text, investigations=inv)
        status = "OK " if block == expect else "FAIL"
        if block != expect:
            ok = False
        print(f"  [{status}] inv={inv} expect_block={expect!s:5} got={block!s:5}  {text[:52]!r}")

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(_selftest())

    if os.environ.get(BYPASS_ENV) == "1":
        sys.exit(0)

    payload = _read_stdin_json()
    transcript = payload.get("transcript_path", "")
    text = _last_assistant_text(transcript)
    investigations = _investigations_since_last_user(transcript)
    block, reason = evaluate(text, investigations)
    if block:
        print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
