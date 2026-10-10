# Personal Claude Playbook

Patterns I've discovered that produce great output. Reuse on every project.

## Pattern: 10 ergonomic mockups before backend

When building any user-facing app, before writing the backend, ask Claude
to produce 10 fully-working static HTML/CSS/JS mockups — each one a
different ergonomic stance, not a color variation.

Serve them via a tiny http.server on a viewer port (51990) with a
single-page viewer (sidebar + iframe + j/k navigation + "open in new tab"
links) at the index.

Pick by feel on the target device (usually mobile). Promote chosen to
ui/, archive the rest. Then build the backend around the chosen UI.

### The exact instruction block to reuse

Phase 0 — UI direction selection (before any backend work)

Build 10 static HTML/CSS/JS mockups in mocks-ui/01/ through /10/. Each
is a different ergonomic stance, NOT a color variation. If two feel
like siblings, redo one.

Spread examples (use as inspiration, not a checklist):
- conversational feed (iMessage-style)
- drop-zone-is-the-page zen minimal
- two-pane utility (power-user dense)
- card stack, thumb-first mobile
- terminal / CLI aesthetic
- physical metaphor (objects on a surface)
- single command bar (Raycast-style)
- gallery grid (Photos.app-style)
- bento dashboard
- notification-center transient feed

Each mock:
- Single self-contained index.html, inline CSS + JS
- Hardcoded realistic sample data
- Works fully — drag/drop, animations, downloads trigger
- Renders at 375px (mobile) AND 1280px (desktop)
- Dark by default, system font, zero external assets
- Looks like a finished product, not a wireframe

Then build a single-page viewer index at the root (port 51990):
- Sidebar list of all 10
- iframe shows the selected one
- j/k or ↑/↓ to navigate
- 1-9,0 number keys to jump
- "Open in new tab ↗" link per mock
- Mobile: sidebar collapses to top bar

STOP after Phase 0. Wait for "go with NN" to pick.

## Pattern: SESSION.md for autonomous runs

Use SESSION.md (not CLAUDE.md) for "what to do this session" briefs.
CLAUDE.md stays the architectural constitution; SESSION.md is per-run.

Always include in SESSION.md:
- "No interrupts — full autonomy" with the explicit short list of
  things that DO warrant stopping (live payments, DNS, destructive
  git, decisions the AI can't make)
- Out-of-scope list (concrete, not aspirational)
- "I will not be available until you're done" framing
- Quality gates per unit shipped
- End-of-run report requirements

## Pattern: Three-pass architecture

For autonomous builds:
1. Risk-first phase (the hardest technical piece first)
2. Glue phases (auth, payment, UI, deploy)
3. Hardening phase (tests, docs, MAINTENANCE.md)

Commit after every green phase. Three-strikes rule on any single
failure (stop after 3 attempts, summarize, don't try a 4th).

## Pattern: Parallel sub-agents for symmetric work

When work decomposes into N independent units (10 pages × 1 form,
20 SKUs × 1 importer), launch parallel sub-agents — one per unit.

## Pattern: homeserver + tmux + bypass-permissions

For multi-hour autonomous runs:
- ssh to a persistent box (homeserver)
- tmux new -s <project>
- claude --dangerously-skip-permissions
- detach, walk away
- Mac sleep doesn't matter; tmux survives

## Add new patterns as you find them

Keep this file. Reference it at the start of every new project. The
patterns compound.
