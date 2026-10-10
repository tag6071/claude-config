#!/usr/bin/python3
"""
PreToolUse hook (Write/Edit/MultiEdit): no unrequested files; keep Markdown lean.

Two gates in one hook (don't spawn a second — fold here):

  A. NO UNREQUESTED NEW FILES — on a Write that CREATES a file (any type):
     - scratch/temp dirs, memory store, plans, generated mirrors → allow.
     - inside a git repo, a code/config file → allow (normal dev work).
     - inside a git repo, a doc-like file (.md/.txt/.csv/.xlsx/.pdf…) → block
       ONCE listing same-type siblings to fold into; re-issue proceeds.
     - OUTSIDE any repo (Documents, Desktop, …) → HARD block, listing
       same-type siblings. Retrying does NOT release it. Releases only when the
       user's latest prompt asked for a file, or the user has replied since the
       block (Claude asked once, user answered). The USER is never prompted.
     Editing/overwriting an existing file is never gated.

  B. CLICKABLE REFS — on any .md write/edit, block when the text contains:
       1. a bare section ref  §N / §N.M  that is NOT a link  -> [§N](#slug)
       2. a code-span `path/x.md` that RESOLVES to a real file -> [x.md](path/x.md)
     Precision: commands/flags/device-names/values/globs/non-resolving *.md stay
     code-spans; refs already inside [text](link) are stripped before scanning.
     Block is fix-and-retry (deterministic — links pass).

Gate B fires only on .md/.mdx/.markdown. Reports every violation at once.
Fail-open on any parse error — never break the harness.

Exits: 0 allow · 2 block (stderr shown to Claude).
Bypass (user, single shell): export CLAUDE_ALLOW_NEW_DOC=1 (A) / CLAUDE_ALLOW_MD_REFS=1 (B)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

DOC_SUFFIXES = {".md", ".mdx", ".markdown"}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}

# Ephemeral working artifacts — NOT permanent codebase docs. Both gates skip these:
# a plan is scratch thinking, not a doc to fold or hyperlink.
PLAN_DIRS = {"plans"}


def is_plan(target: Path) -> bool:
    parts_lower = {p.lower() for p in target.parts}
    if PLAN_DIRS & parts_lower:
        return True
    name = target.name.lower()
    return name == "plan.md" or name.startswith("plan-")


def is_memory(target: Path) -> bool:
    """A file in the auto-memory store (~/.claude/projects/<slug>/memory/).

    Both gates skip these. The store's schema is ONE FACT PER FILE behind a MEMORY.md
    index, and it links with [[wiki-refs]], not markdown links — so Gate A's "fold into
    a sibling" and Gate B's clickable-ref rule are both structurally wrong here. Gate A
    fired on every single memory write before this exemption; a guard that is wrong on
    100% of a directory's writes is a guard that trains you to ignore it.
    """
    parts_lower = [p.lower() for p in target.parts]
    return ".claude" in parts_lower and "memory" in parts_lower


# A generated 1:1 mirror of a source file declares itself on line 1, e.g.
#   <!-- Translated from: docs/source.pdf -->
# Both gates are structurally wrong on these. Gate A says "fold into a sibling",
# but folding two translations into one file destroys the mirror mapping the
# generator depends on; Gate B's clickable-ref rule would rewrite quoted source
# text. A translated-docs folder hit this on every write in one run — a
# guard that is wrong on every write in a directory trains you to ignore it.
MIRROR_MARKER_RE = re.compile(
    r"^\s*<!--\s*(?:translated|generated|converted|extracted)\s+from:", re.IGNORECASE
)


def is_mirror(text: str) -> bool:
    return bool(text) and bool(MIRROR_MARKER_RE.match(text.lstrip("﻿")))


# Gate A (new-file fold)
NEWDOC_BYPASS = "CLAUDE_ALLOW_NEW_DOC"
ACK_DIR = Path(tempfile.gettempdir()) / "claude-newdoc-ack"
HARD_ACK_DIR = Path(tempfile.gettempdir()) / "claude-newfile-block"
ACK_WINDOW_S = 600
# Files a person reads, not code a build runs. Gated even inside a repo.
DOC_LIKE = DOC_SUFFIXES | {
    ".txt", ".rst", ".org", ".csv", ".tsv", ".xlsx", ".xls", ".ods",
    ".docx", ".doc", ".odt", ".pdf", ".pptx", ".rtf",
}
SCRATCH_ROOTS = [
    Path(tempfile.gettempdir()).resolve(), Path("/private/tmp"), Path("/private/var/folders"),
]
# The user's latest prompt asked for a file. Pasted text is stripped first — it's not theirs.
ASKED_RE = re.compile(
    r"\b(files?|spreadsheets?|excel|csv|pdfs?|docx|word doc\w*|readme|scripts?|"
    r"save\w*|export\w*|download\w*|create|generate|make (a|an|me)|write (it|this|that|them) (to|into|down)|"
    r"datei\w*|speicher\w*|erstell\w*|anlegen)\b",
    re.IGNORECASE,
)
PASTED_RE = re.compile(r"<pasted_content\b.*?</pasted_content[^>]*>", re.DOTALL)
TRANSCRIPT_TAIL = 2_000_000

# Gate B (clickable refs)
REFS_BYPASS = "CLAUDE_ALLOW_MD_REFS"
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
INLINE_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
HEADING_LINE_RE = re.compile(r"(?m)^\s*#{1,6}\s.*$")
CODESPAN_RE = re.compile(r"`([^`]+)`")
SECTION_REF_RE = re.compile(r"§\s*\d+(?:\.\d+)*")


def repo_root(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


def existing_ancestor(target: Path) -> Path:
    """Nearest existing dir — a new file in a new folder is judged by where it lands, not cwd."""
    for d in target.parents:
        if d.is_dir():
            return d
    return Path("/")


# ---- Gate A: new-file fold ------------------------------------------------

def same_kind(target: Path) -> set[str]:
    s = target.suffix.lower()
    return DOC_SUFFIXES if s in DOC_SUFFIXES else {s}


def sibling_docs(target: Path) -> list[Path]:
    kinds = same_kind(target)
    out: list[Path] = []
    for folder in {target.parent, target.parent.parent}:
        if not folder.is_dir():
            continue
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in kinds and p != target:
                out.append(p)
    return sorted(set(out))


def is_scratch(target: Path) -> bool:
    try:
        resolved = existing_ancestor(target).resolve() / target.name
    except OSError:
        return False
    return any(resolved.is_relative_to(r) for r in SCRATCH_ROOTS)


def user_prompts(transcript: str | None) -> list[tuple[float, str]]:
    """(epoch, text) of the user's real prompts — no tool results, no hook feedback."""
    if not transcript:
        return []
    try:
        with open(transcript, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - TRANSCRIPT_TAIL))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    out: list[tuple[float, str]] = []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") != "user" or e.get("isMeta"):
            continue
        c = (e.get("message") or {}).get("content")
        if isinstance(c, list):
            if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
                continue
            c = " ".join(b.get("text", "") for b in c if isinstance(b, dict))
        if not isinstance(c, str) or not c.strip():
            continue
        try:
            ts = dt.datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp()
        except (KeyError, ValueError, AttributeError):
            continue
        out.append((ts, c))
    return out


def gate_outside_repo(target: Path, transcript: str | None, show) -> int:
    """New file in the user's own folders. Hard block — retry never releases. 0 allow · 2 block."""
    prompts = user_prompts(transcript)
    if prompts and ASKED_RE.search(PASTED_RE.sub(" ", prompts[-1][1])):
        return 0
    ack = HARD_ACK_DIR / ack_file(target).name
    if ack.exists() and prompts and prompts[-1][0] > ack.stat().st_mtime:
        ack.unlink(missing_ok=True)
        return 0
    HARD_ACK_DIR.mkdir(parents=True, exist_ok=True)
    ack.write_text(str(target))

    candidates = sibling_docs(target)
    listing = "\n".join(f"  • {show(p)}" for p in candidates[:25])
    fold = (f"Same-type files already there — ADD TO ONE with Edit:\n{listing}\n"
            if candidates else "No same-type file there to add to.\n")
    sys.stderr.write(
        f"BLOCKED by ~/.claude/hooks/doc-guard.py [new-file] — creating: {show(target)}\n\n"
        "The user did not ask for a file. They hate folder pollution.\n"
        f"{fold}"
        "Otherwise put the content in the chat. If a file is genuinely needed, ask the user ONE\n"
        "question naming the path; their reply releases this exact path. Re-issuing without\n"
        "asking stays blocked. Scratch work goes in the session scratchpad (always allowed).\n"
        f"Bypass (user, single shell): export {NEWDOC_BYPASS}=1\n"
    )
    return 2


def same_stem_docs(target: Path, root: Path) -> list[Path]:
    stem = target.stem.lower()
    if len(stem) < 3:
        return []
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in DOC_SUFFIXES and p.stem.lower() == stem and p != target:
                out.append(p)
    return sorted(set(out))


def ack_file(path: Path) -> Path:
    return ACK_DIR / hashlib.sha256(str(path).encode()).hexdigest()[:16]


def gate_new_doc(target: Path, root: Path | None, show) -> int:
    """Only for a Write creating a NEW doc. 0 allow · 2 block."""
    if os.environ.get(NEWDOC_BYPASS) == "1":
        return 0
    ack = ack_file(target)
    if ack.exists() and (time.time() - ack.stat().st_mtime) < ACK_WINDOW_S:
        try:
            ack.unlink()
        except OSError:
            pass
        return 0
    ACK_DIR.mkdir(parents=True, exist_ok=True)
    ack.write_text(str(target))

    candidates = sibling_docs(target)
    if root:
        candidates += [p for p in same_stem_docs(target, root) if p not in candidates]
    if candidates:
        listing = "\n".join(f"  • {show(p)}" for p in candidates[:25])
        body = f"Docs already in that folder — FOLD INTO ONE unless none fits:\n{listing}\n"
    else:
        body = "No docs in that folder — a new file may be right. Still: is there a top-level doc this belongs in?\n"
    sys.stderr.write(
        f"PAUSED by ~/.claude/hooks/doc-guard.py [new-doc] — creating: {show(target)}\n\n"
        f"{body}\n"
        "Extend an existing doc over spawning a new one. Be concise — no textbook dumps.\n"
        "If folding is genuinely wrong, RE-ISSUE this exact Write and it proceeds.\n"
    )
    return 2


# ---- Gate B: clickable refs ----------------------------------------------

def gate_refs(target: Path, text: str, root: Path | None) -> int:
    """0 allow · 2 block."""
    if os.environ.get(REFS_BYPASS) == "1":
        return 0
    md_dir = target.parent
    t = FENCE_RE.sub(" ", text)
    t = INLINE_LINK_RE.sub(" ", t)
    t_sections = HEADING_LINE_RE.sub(" ", CODESPAN_RE.sub(" ", t))

    section_hits = sorted(set(SECTION_REF_RE.findall(t_sections)))

    file_hits: list[str] = []
    for span in CODESPAN_RE.findall(t):
        c = span.strip()
        if " " in c or "*" in c or not c.lower().endswith((".md", ".mdx", ".markdown")):
            continue
        rel = c[2:] if c.startswith("./") else c
        candidates = [md_dir / c, md_dir / rel]
        if root:
            candidates.append(root / rel)
        if any(p.exists() and p.is_file() for p in candidates):
            file_hits.append(c)
    file_hits = sorted(set(file_hits))

    if not section_hits and not file_hits:
        return 0

    out = ["BLOCKED by ~/.claude/hooks/doc-guard.py [refs] — Markdown refs must be CLICKABLE, not bare text / code-span noise.\n"]
    if section_hits:
        out.append("Bare section refs → make each [§N](#slug):")
        out.append("  " + "  ".join(section_hits))
        out.append(
            "  slug = target heading, lowercased, punctuation/emoji dropped, spaces→hyphens.\n"
            "  e.g. `## 5. Restore the seed` → [§5](#5-restore-the-seed). Keep headings slug-safe.\n"
        )
    if file_hits:
        out.append("File refs trapped in code-spans → make each [name](relative/path):")
        for c in file_hits:
            out.append(f"  `{c}`  →  [{Path(c).name}]({c})")
        out.append("")
    out.append(
        "Fix ALL of these in this ONE write — never patch one ref at a time. "
        "Keep code-spans for commands, flags, device names, values, globs, gitignored files.\n"
        f"Bypass (user, single shell): export {REFS_BYPASS}=1"
    )
    sys.stderr.write("\n".join(out) + "\n")
    return 2


# ---- driver ---------------------------------------------------------------

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool = payload.get("tool_name", "")
    if tool not in {"Write", "Edit", "MultiEdit"}:
        return 0
    ti = payload.get("tool_input") or {}
    raw = ti.get("file_path") or ""
    if not raw:
        return 0
    target = Path(raw).expanduser()
    is_md = target.suffix.lower() in DOC_SUFFIXES
    creating = tool == "Write" and not target.exists()
    if not is_md and not creating:
        return 0
    if is_plan(target) or is_memory(target):
        return 0

    if tool == "Write":
        text = ti.get("content") or ""
    elif tool == "Edit":
        text = ti.get("new_string") or ""
    else:
        text = "\n".join(e.get("new_string", "") for e in ti.get("edits") or [])

    if is_mirror(text):
        return 0

    root = repo_root(existing_ancestor(target))

    def show(p: Path) -> str:
        try:
            return str(p.relative_to(root)) if root else str(p)
        except ValueError:
            return str(p)

    # Gate B first (Markdown writes); then Gate A (new files only).
    if is_md and text:
        rc = gate_refs(target, text, root)
        if rc:
            return rc
    if not creating or os.environ.get(NEWDOC_BYPASS) == "1" or is_scratch(target):
        return 0
    if root is None:
        return gate_outside_repo(target, payload.get("transcript_path"), show)
    if target.suffix.lower() in DOC_LIKE:
        return gate_new_doc(target, root, show)
    return 0


if __name__ == "__main__":
    sys.exit(main())
