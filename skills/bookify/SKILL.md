---
name: bookify
description: Lock a chapter-worthy moment from a session into the project's book/ — as a BACKLOG seed, journal entry, or chapter draft, depending on substance. Trigger phrases include "/bookify", "bookify this", "is this bookworthy", "save this for the book". Invoked when the user wants something captured in their book/ directory before it leaves working memory.
---

# /bookify — Lock a moment into the book

Called when the user invokes `/bookify` (or equivalent phrasing) to capture
a chapter-worthy moment into the project's book/ directory. The skill
decides FORMAT (BACKLOG seed vs journal vs chapter draft) based on
substance, writes the content matching the book's existing voice, updates
TOC.md if a new chapter, and commits.

## When to use

User explicitly invokes `/bookify` or equivalent: "bookify this", "is this
bookworthy", "save this for the book", "lock this moment in", "add to the
book."

DO NOT autonomously bookify without invocation. Don't write to `book/` unilaterally. The slash-command IS the
authorization signal. Without it, flag the moment in conversation and let
the user invoke if they want.

## Prerequisites

The project must have a `book/` directory with the standard scaffold:

```
book/
├── README.md
├── TOC.md
├── CONVENTIONS.md       (voice + rules; READ THIS to match tone)
├── BACKLOG.md
├── chapters/cNN-slug.md
└── journal/YYYY-MM-DD-slug.md
```

If `book/` doesn't exist, STOP and tell the user this project isn't
book-ified — don't create the scaffold under `/bookify`; that's a
separate "init a book" decision.

## Steps

### 1. Identify the moment being bookified

Extract from immediate context: what specific insight, decision, debugging
arc, or pattern is the user pointing at? If unclear, ask ONE specific
question (e.g., "the dir-naming decision we just made, or the broader
'how to organize IaC subsystems' theme?"). Don't widen to "everything we
talked about today."

### 2. Assess bookworthiness

The moment qualifies if at least TWO of these are true:

- It teaches a concrete principle a reader could apply elsewhere
- It came from a real incident or design decision (not abstract)
- The user explicitly wants to remember it in months / years
- It's different from what's already in `book/chapters/` and
  `book/BACKLOG.md` (grep before writing)
- It has a clear "before / after" or "I learned X" shape

If fewer than two qualify, the right move is "this isn't bookworthy yet —
let it accumulate with sibling moments and revisit." Tell the user.

### 3. Decide format

| Format | When |
|---|---|
| **Chapter draft** | Single coherent narrative arc, ~1500-2500 words of substance, has its own opening / middle / lesson / closing. Stands alone as a reader's takeaway. |
| **Journal entry** | Same-day or same-week capture of a multi-thread experience. Raw, chronological, messy-but-true. Will inform a future polished chapter. Write-immediately rule (per `book/CONVENTIONS.md`). |
| **BACKLOG seed** | Smaller than a chapter, OR fits as a SECTION inside an already-planned chapter, OR needs sibling moments before chapter-shape emerges. Single bullet, ~3-15 lines. |

When in doubt: BACKLOG seed. Easier to promote later than to retract a
half-formed chapter.

### 4. Match the existing voice

READ at least one already-published chapter (status `✓` in `TOC.md`) plus
`book/CONVENTIONS.md` before writing. Match:

- First-person ("I", not "you")
- Incident-anchored (cite the specific commit / journal / date)
- Visual where the topic is spatial / relational / structural 
- No motivational filler, no "let me share with you", no preamble
- Honest about open questions ("What I still don't know" sections are
  the norm)

### 5. Write the content

Match the destination format's template:

**Chapter draft template** (use existing `cNN-slug.md` files as the
canonical shape — opening callouts ("In one sentence", "Prerequisites",
"Lab artifact"), question-that-prompted-this, what-I-didn't-know-going-in,
the-picture (with visual), the-explanation, what-tripped-me-up, what-I-
still-don't-know, see-also).

**Journal entry template** (see existing `book/journal/*.md`): topics
covered today, things to promote to chapters, raw notes — what actually
happened, commits landed today.

**BACKLOG entry template**: single bullet, format
`- YYYY-MM-DD — short description ... (chapter target: cNN, or "?" if
unclear.)` plus 3-15 lines of "why this matters" if not obvious.

### 6. Write to the right path + update TOC

- BACKLOG → append to `book/BACKLOG.md` under `## Open backlog` (or
  `## Promoted to chapters` if this is also creating a chapter at the
  same time)
- Journal → write to `book/journal/YYYY-MM-DD-<slug>.md`
- Chapter → write to `book/chapters/cNN-<slug>.md` AND update
  `book/TOC.md` to add the new row with status `⚙` (drafting)

### 7. Cross-references

For chapter drafts, populate the See-also section with concrete pointers:

- Related LESSONS entries (`docs/LESSONS.md`)
- Sibling / counterpoint chapters
- Commit hashes that established the artifact
- ROADMAP phase if relevant

For BACKLOG seeds, cite at minimum the commit hash that triggered the
moment (`git log -1 --format='%h'` is fine if it's the most recent commit).

### 8. Commit

```bash
git -C <project-root> add book/<paths-touched>
git -C <project-root> commit -m "book(<kind>): <slug> — <one-liner>"
```

Use `book(chapter):` for chapter drafts, `book(journal):` for journal
entries, `book(backlog):` for BACKLOG seeds. Include `Co-Authored-By:` if
the project pattern uses it.

## Anti-patterns

- ❌ Don't force a chapter draft out of every invocation. BACKLOG is
  the safest default; promote later when sibling moments accumulate.
- ❌ Don't write to `book/` without the `/bookify` invocation (or
  equivalent explicit user authorization).
- ❌ Don't lose the incident anchor. Every entry cites a specific
  moment / decision / commit. Without that, it reads as detached
  theory.
- ❌ Don't widen scope past the moment being bookified. If the user
  pointed at one insight, write about THAT insight, not the broader
  theme that surrounds it.
- ❌ Don't auto-promote BACKLOG seeds to chapters at `/bookify` time.
  That's a separate user-invoked action.
- ❌ Don't duplicate content. Grep `book/chapters/`, `book/journal/`,
  and `book/BACKLOG.md` for the topic first.
