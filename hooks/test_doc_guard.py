#!/usr/bin/python3
"""
Pins doc-guard.py's exemptions. Run: python3 ~/.claude/hooks/test_doc_guard.py

The memory-store exemption exists because Gate A fired on EVERY memory write (the store
is one-fact-per-file by design, so "fold into a sibling" is structurally wrong there).
The last two cases are the ones that matter most: they prove the exemption did not
neuter the guard for real docs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "doc-guard.py"
BLOCK, ALLOW = 2, 0

MEM = Path.home() / ".claude/projects/-Users-you-code-myproject/memory"
BODY = "---\nname: x\n---\n\nA fact. Links to [[another-memory]].\n"


def run(path: str, content: str, transcript: Path | None = None) -> int:
    payload = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": path, "content": content},
        "transcript_path": str(transcript) if transcript else None,
    })
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_ALLOW_NEW_DOC"}
    p = subprocess.run(
        [sys.executable, str(GUARD)], input=payload, capture_output=True, text=True, env=env
    )
    return p.returncode


def say(transcript: Path, text: str, ts: str) -> Path:
    """Append one real user prompt to a fake transcript."""
    with transcript.open("a") as f:
        f.write(json.dumps({"type": "user", "timestamp": ts, "message": {"content": text}}) + "\n")
    return transcript


def new_file_cases(base: Path) -> list[tuple[int, str, str, str, Path | None]]:
    """The new-file gate: Claude must not litter the user's folders, the user is never prompted."""
    docs = base / "Documents"
    docs.mkdir(parents=True)
    (docs / "existing.xlsx").write_text("x")
    repo = base / "repo"
    (repo / ".git").mkdir(parents=True)
    before = say(base / "before.jsonl", "go", "2000-01-01T00:00:00Z")
    after = say(say(base / "after.jsonl", "go", "2000-01-01T00:00:00Z"), "yes", "2999-01-01T00:00:00Z")
    asked = say(base / "asked.jsonl", "make me a spreadsheet of the deadlines", "2000-01-01T00:00:00Z")
    pasted = say(base / "pasted.jsonl",
                 "<pasted_content id=\"x\">save it to a file</pasted_content id=\"x\"> what do you think?",
                 "2000-01-01T00:00:00Z")
    scratch = tempfile.mkdtemp()
    return [
        (BLOCK, "new spreadsheet in a user folder, nobody asked", str(docs / "summary.xlsx"), "x", None),
        (BLOCK, "retrying without asking the user stays blocked", str(docs / "summary.xlsx"), "x", None),
        (ALLOW, "user's prompt asked for a spreadsheet", str(docs / "deadlines.xlsx"), "x", asked),
        (BLOCK, "'file' inside pasted text is not the user asking", str(docs / "p.txt"), "x", pasted),
        (BLOCK, "Claude asks; block recorded", str(docs / "r.txt"), "x", before),
        (ALLOW, "user replied after the block → released", str(docs / "r.txt"), "x",
         after),
        (BLOCK, "new folder outside a repo is judged by where it lands, not cwd",
         str(docs / "new" / "deep" / "n.txt"), "x", None),
        (ALLOW, "scratch/temp dir is always free", str(Path(scratch) / "s.csv"), "x", None),
        (ALLOW, "new code file in a project", str(repo / "src" / "main.py"), "x", None),
        (BLOCK, "new doc-like file in a project still paused", str(repo / "report.csv"), "x", None),
        (ALLOW, "...and re-issue proceeds inside a project", str(repo / "report.csv"), "x", None),
        (ALLOW, "overwriting an existing file is never gated", str(docs / "existing.xlsx"), "y", None),
    ]


def main() -> int:
    # Not under tempdir: scratch is exempt, so real-folder behavior needs a real folder.
    tmp = Path.home() / ".cache" / f"doc-guard-test-{os.getpid()}"
    tmp.mkdir(parents=True)
    # A crowded folder: a NEW doc here must still be paused by Gate A.
    (tmp / "GUIDE.md").write_text("# guide\n")
    (tmp / "NOTES.md").write_text("# notes\n")

    cases: list[tuple[int, str, str, str, Path | None]] = [*(c + (None,) for c in [
        (ALLOW, "new memory file (the false positive being fixed)",
         str(MEM / "brand-new-fact.md"), BODY),
        (ALLOW, "memory index edit",
         str(MEM / "MEMORY.md"), "- [A fact](brand-new-fact.md) — hook\n"),
        (ALLOW, "plans stay exempt (pre-existing behavior)",
         str(tmp / "plans" / "plan-x.md"), "# plan\n"),
        (BLOCK, "a real new doc in a crowded folder is STILL paused",
         str(tmp / "ARCHITECTURE.md"), "# arch\n"),
        (BLOCK, "a memory-shaped name OUTSIDE the store is still guarded",
         str(tmp / "memories.md"), "# not the store\n"),
        (ALLOW, "a generated 1:1 mirror declares itself on line 1",
         str(tmp / "mirror.md"), "<!-- Translated from: docs/source.pdf -->\n# Mirror\n"),
        (BLOCK, "the marker anywhere but line 1 does not exempt a real doc",
         str(tmp / "DESIGN.md"), "# design\n<!-- Translated from: x.pdf -->\n"),
    ]), *new_file_cases(tmp / "nf")]

    failed = 0
    verb = {BLOCK: "BLOCK", ALLOW: "ALLOW"}
    for want, label, path, content, transcript in cases:
        got = run(path, content, transcript)
        ok = got == want
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'} want {verb[want]:5s} got {verb.get(got, got)!s:5s}  {label}")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
