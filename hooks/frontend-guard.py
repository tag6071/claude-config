#!/usr/bin/env python3
"""
PostToolUse:Edit|Write|MultiEdit — FRONTEND GUARD (live, mid-session).

The commit gate (stack-conformance lint via /install-lint-rails) is the
AUTHORITATIVE hard stop and the source of truth. This hook is its fast mirror:
it fires the moment a frontend file is edited — triggered by the WORK, not by a
keyword in the prompt and not by anyone remembering the rules — and feeds any
off-stack pattern straight back to the model so it self-corrects NOW instead of
at commit. Patterns are a strict subset of the .sh checks. NO escape hatch —
there is no bypass comment (the no_escape_comments lock bans them); fix the line.

Catches (block-class only, to stay quiet otherwise):
  inline style hardcoding a design value / <style> block
  raw hex/rgb/hsl colour      (token sheets exempt)
  off-scale type/spacing
  native <select> / custom modal  (only if shadcn present)

Protocol: reads JSON on stdin. exit 0 = clean/not-applicable (silent);
exit 2 = stderr fed back to the model as actionable feedback. Never blocks the
edit itself (it already ran) — it nudges the fix.
Bypass: CLAUDE_SKIP_FRONTEND_GUARD=1
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if os.environ.get("CLAUDE_SKIP_FRONTEND_GUARD"):
    sys.exit(0)

FRONTEND_EXT = {".tsx", ".jsx", ".css", ".scss"}
TOKEN_FILE = re.compile(r"(tailwind\.config\.|components\.json$|(^|/)(globals|index|[Aa]pp|theme)\.(css|scss)$|tokens\.(css|scss)$)")
EXCLUDED_DIR = re.compile(r"(^|/)(node_modules|dist|build|\.archive[a-zA-Z0-9._-]*)/")

# An inline style is off-stack when it HARDCODES a design-scale value, not
# because it is inline. A CSS-var injection or a computed position
# (a per-item `--hue` custom prop, a measured width) is irreducible — there is
# no utility class for a value unknown until runtime. That is why
# stack-conformance gates routinely leave `no_inline_styles` uninstalled and
# enforce the rule that actually matters instead: no raw number on a
# rhythm/type property. Mirroring that keeps this hook the strict SUBSET it
# claims to be; a blanket inline-style match made it a superset and fired on
# lines the authoritative gate passes. Property list + the `[1-9]` (so `0`
# resets stay legal) track no_arbitrary_dimensions.sh / no_inline_styles.sh exactly.
HARDCODED_STYLE_VALUE = re.compile(
    r"\b(fontSize|padding|paddingLeft|paddingRight|paddingTop|paddingBottom"
    r"|margin|marginLeft|marginRight|marginTop|marginBottom|gap)\s*:\s*[\"']?[1-9]"
    r"|font\s*:\s*[\"'][0-9]+(\.[0-9]+)?px"
)
INLINE_STYLE_OPEN = re.compile(r"style=\{\{")
STYLE_TAG = re.compile(r"<style[\s>]")


MAX_STYLE_LINES = 8


def style_object_text(lines: list[str], idx: int) -> str:
    """Text of the style object opening on lines[idx], brace-matched.

    A fixed forward window is not good enough: two style objects within a few
    lines of each other let a later one's hardcoded value be reported against an
    earlier, legal line (a `marginTop: 0` reset). Tracking brace depth keeps each
    object's values attached to the object they belong to.
    """
    m = INLINE_STYLE_OPEN.search(lines[idx])
    if not m:
        return ""
    chunk = lines[idx][m.end():]
    depth = 2  # the two braces of `style={{`
    parts = []
    for line in [chunk, *lines[idx + 1:idx + MAX_STYLE_LINES]]:
        for ch in line:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    parts.append(line)
                    return " ".join(parts)
        parts.append(line)
    return " ".join(parts)


def inline_style_hit(lines: list[str], idx: int) -> bool:
    """A <style> block, or an inline style object carrying a hardcoded value.

    Anchored on lines[idx] so the reported L number is the line that OPENS the
    style, while the values it is judged on are that object's own.
    """
    if STYLE_TAG.search(lines[idx]):
        return True
    return bool(HARDCODED_STYLE_VALUE.search(style_object_text(lines, idx)))


# (label, compiled regex OR callable(lines, idx), needs_shadcn, applies-to predicate)
RULES = [
    ("inline style hardcodes a design value → the named scale tokens",
     inline_style_hit, False,
     lambda suf, tok: suf in {".tsx", ".jsx"}),
    ("raw colour literal → a design token",
     re.compile(r"#[0-9a-fA-F]{3,4}\b|#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?\b|\b(rgba?|hsla?)\("), False,
     lambda suf, tok: not tok),
    ("off-scale type/spacing → the named scale (text-sm/p-4/gap-section)",
     re.compile(r"\b(text|leading|tracking|gap|space-[xy]|[pm][xytblrse]?)-\[[0-9.]+(px|rem|em)\]"
                r"|(font-size|line-height)\s*:\s*[0-9.]+px"), False,
     lambda suf, tok: not tok),
    ("hand-rolled primitive → shadcn Select/Dialog (focus-trap + a11y)",
     re.compile(r"<select[\s/>]|<dialog[\s/>]|role=(\"|')?dialog|aria-modal"), True,
     lambda suf, tok: suf in {".tsx", ".jsx"}),
]


LINE_COMMENT = re.compile(r"(?<!:)//")


def blank_comments(lines: list[str]) -> list[str]:
    """Blank comment CONTENT, preserving line count (hit messages cite L numbers).

    Comments are commentary, never shipped style, so no rule here can apply to them.
    Without this, a GitHub issue ref in a comment (`// react-rnd issue #984`) reads as
    a raw hex colour and blocks the write — a false positive that costs a round-trip
    and teaches nothing. `//` only starts a comment when not preceded by `:`, so a
    `https://` URL doesn't swallow the rest of its line.
    """
    out: list[str] = []
    in_block = False
    for line in lines:
        buf: list[str] = []
        i = 0
        while i < len(line):
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    break
                in_block = False
                i = end + 2
                continue
            start = line.find("/*", i)
            m = LINE_COMMENT.search(line, i)
            slash = m.start() if m else -1
            if start != -1 and (slash == -1 or start < slash):
                buf.append(line[i:start])
                in_block = True
                i = start + 2
            elif slash != -1:
                buf.append(line[i:slash])
                break
            else:
                buf.append(line[i:])
                break
        out.append("".join(buf))
    return out


def find_root(start: Path) -> Path | None:
    """Walk up to the nearest dir holding a React package.json."""
    for d in [start, *start.parents]:
        pj = d / "package.json"
        try:
            if pj.is_file() and re.search(r'"react"\s*:', pj.read_text("utf-8", "ignore")):
                return d
        except OSError:
            pass
        if d == d.parent:
            break
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    fp = (data.get("tool_input") or {}).get("file_path") or ""
    if not fp:
        return 0
    path = Path(fp)
    if path.suffix not in FRONTEND_EXT or not path.is_file():
        return 0

    root = find_root(path.parent)
    if root is None:                       # not a React project — not our jurisdiction
        return 0
    rel = str(path).replace(str(root) + "/", "")
    if EXCLUDED_DIR.search(rel):           # archived/generated code is not live UI
        return 0
    is_token = bool(TOKEN_FILE.search(rel))
    has_shadcn = (root / "src" / "components" / "ui").is_dir() or (root / "components" / "ui").is_dir()

    try:
        if path.stat().st_size > 600_000:
            return 0
        lines = blank_comments(path.read_text("utf-8", "ignore").splitlines())
    except OSError:
        return 0

    hits: list[str] = []
    for label, pat, needs_shadcn, applies in RULES:
        if not applies(path.suffix, is_token):
            continue
        if needs_shadcn and not has_shadcn:
            continue
        for i, line in enumerate(lines, 1):
            # Callable rules read forward from this line: a style object is
            # routinely wrapped, so its values are not on the line that opens
            # it. They stay anchored on lines[i-1] for the L number.
            hit = pat(lines, i - 1) if callable(pat) else pat.search(line)
            if hit:
                hits.append(f"  L{i}: {label}")
                break  # one hit per rule is enough to make the point

    if not hits:
        return 0

    print(
        f"frontend-guard — {rel} has off-stack patterns (the commit gate will block these):\n"
        + "\n".join(hits)
        + "\n↳ fix now: Tailwind utilities + your named scale tokens, shadcn primitives."
        "\n↳ NO escape hatch — make the line actually compliant.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
