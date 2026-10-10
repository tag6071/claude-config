---
name: claudify
description: The single skill to make any existing repo fast for Claude Code. Phase 1 (FLOOR, any repo) drops a skinny CLAUDE.md, scaffolds .claude/skills/, ensures the global SessionStart context hook. Phase 2 (DEEP INDEXABILITY) auto-extends ON MATURE REPOS — CODE_MAP, LESSONS (commit-hash provenance), API-QUIRKS, scripts manifest, a "Where to look" nav table, and make audit-docs/ai-brief guardrails. Subsumes the former /ai-indexability skill. Trigger phrases include "/claudify", "claudify this repo", "set up this repo for Claude", "make this codebase efficient for LLMs", "make this repo AI-indexable", "add CODE_MAP to this repo", "set up the indexability docs". Modes: "/claudify" = floor + auto-deep if mature; "/claudify floor" = floor only; "/claudify deep" = force deep. Idempotent — re-running audits and upgrades, never blind-overwrites. Do NOT use to scaffold a NEW empty project (use `scaffold` first) or to add one skill to an already-claudified repo (just write it).
---

# Claudify

Make any existing repo blazingly fast for Claude Code sessions. Two phases:

- **Phase 1 — FLOOR** (any repo): skinny `CLAUDE.md`, `SessionStart` context hook, `.claude/skills/` scaffold.
- **Phase 2 — DEEP INDEXABILITY** (mature repos only): the navigation surface — `CODE_MAP`, `LESSONS`, `API-QUIRKS`, scripts manifest, a "Where to look" nav table, and audit guardrails — so a fresh session cold-starts in <2k tokens and never hunts to orient.

Phase 1 always runs. Phase 2 auto-extends only when the repo has earned it (the maturity gate). Exploration runs in an `Explore` subagent so its grep noise dies in the subagent's context, not the user's.

## Invocation modes

- **`/claudify`** — Phase 1, then auto-extend to Phase 2 **if the repo is mature** (maturity gate below).
- **`/claudify floor`** — Phase 1 only. Skip Phase 2 even on a mature repo.
- **`/claudify deep`** — force Phase 2 even on a borderline repo (you know it's worth it).

## Mental model — non-negotiable

Every token in `CLAUDE.md` is paid every session, forever. Be ruthless:

- **IN**: things derivable only from human knowledge (intent, conventions, gotchas) or expensive to derive at runtime (exact build/test/lint commands).
- **OUT**: things grep can find in 100ms (file contents, function bodies, full directory trees, dependency lists already in `package.json`).

The win is not preloading the codebase. The win is making on-demand loading cheap. A fat `CLAUDE.md` is the **opposite** of efficient. The Phase-2 nav docs are how you make on-demand loading cheap WITHOUT inflating CLAUDE.md.

Target: ~80 lines for generated `CLAUDE.md` (Phase 1). Hard cap: 120 lines. If exceeded, the survey was wrong — cut. (The Phase-2 nav table is a handful of additional rows, not prose.)

---

# Phase 1 — FLOOR (always)

### Step 1 — Detect state (read-only, no writes yet)

Report in one line BEFORE touching anything:

- Is current dir a git repo? (`git rev-parse --git-dir`)
- Does `CLAUDE.md` exist at repo root? → create vs audit-and-upgrade.
- Does `.claude/skills/` exist? → preserve.
- Does `.claude/settings.json` exist with hooks? → preserve.
- Does global `~/.claude/settings.json` have a `SessionStart` hook? → install only if missing.

If not a git repo: ask the user whether to `git init` first or proceed without commit. Do not init silently.

### Step 2 — Survey the repo (Explore subagent)

Spawn ONE `Explore` subagent. Survey for BOTH phases at once (survey once, use twice):

> Survey this repo for a `CLAUDE.md` bootstrap + navigation index. Report concisely (under 350 words):
> 1. Primary language(s) and version(s) (from `go.mod`, `pyproject.toml`, `package.json`, `Cargo.toml`, etc.).
> 2. Exact commands for: build, test, lint, format, run. Pull from `package.json` scripts, `Makefile`, `justfile`, `pyproject.toml [tool.*]`, README, or the most authoritative source. If unknown, say so — do not invent.
> 3. Top-level directory layout — 5–10 dirs at root with one-line purpose each. Do NOT recurse.
> 4. Entry points (main file, server bootstrap, CLI entry).
> 5. Any unusual layout, custom tooling, or non-obvious convention worth a "gotcha" line.
> 6. (Phase-2 signals) Repo maturity: commit count (`git rev-list --count HEAD`), age of first commit, total source LOC. Files >500 lines (candidates for CODE_MAP). Is there a `scripts/` dir? Is there an external-API surface worth quirk-documenting? Does any existing `CLAUDE.md` already have a nav table?
> 7. (Mock-backend signal) Does a frontend here call an API? If so: is there an API contract (`openapi.yaml` / `swagger.json`), and is there a mock layer (`msw` in `package.json`, a `mocks/` dir, a `handlers.ts`)? Report which of the three are MISSING — report only, add nothing.
> Do NOT dump file contents or function bodies.

Subagent's grep output stays in its context; only the summary returns. This is the single biggest token saver.

### Step 3 — Write the skinny CLAUDE.md

Use this exact structure. Populate from survey output. Omit any section that genuinely has nothing to say (better empty than padded).

```
# <Repo Name>

<One sentence: what this repo is and who/what it serves.>

## Stack

- <Language> <version>
- <Runtime / framework if any>
- <Up to 5 key deps — name and one-word "why">

## Layout

- `<dir>/` — <one line>
- `<dir>/` — <one line>
(5–10 entries, top-level only — do not enumerate files)

## Commands

- Run:    `<exact command>`
- Test:   `<exact command>`
- Lint:   `<exact command>`
- Format: `<exact command>`
- Build:  `<exact command>` (omit if not applicable)

## Conventions

- <thing not derivable from reading the code>
(3–7 bullets max. Repo-specific only. No generic "use clean code".)

## Gotchas

- <surprising thing that bit a real human>
(3–5 bullets. Things that would cost an hour of debugging. No hypotheticals.)
```

Anti-patterns for the generated `CLAUDE.md`:

- ❌ No file contents. ❌ No function signatures. ❌ No restating filenames.
- ❌ No enumerating files — only directories.
- ❌ No "best practices" boilerplate — only repo-specific facts.
- ❌ No prose paragraphs — bullets and short lines only.

### Step 4 — Audit-vs-create logic (idempotent, no prompt)

If `CLAUDE.md` already exists: **merge silently** — preserve all user prose, refresh only the deterministic sections (Commands, Layout, Stack) from the survey. Safe default, what 99% of re-runs want.

If the user explicitly requests a different action ("replace it", "show me the diff first"), honor it. Otherwise don't ask, just merge — by the time the user invokes `/claudify` they've opted in, and asking hangs under `--dangerously-skip-permissions`.

If creating fresh: write it directly.

### Step 5 — Scaffold `.claude/skills/`

If `.claude/skills/` is missing, create it with a single `README.md`:

```
# Repo-specific skills

When a repeated workflow surfaces (e.g. "add a new API route", "write a
migration", "deploy to staging"), capture it here as a SKILL.md.

## When to add a skill (signal, not count)

At the SECOND occurrence of any pattern, pause and ask:
1. **Cost** — did this take >5 minutes?
2. **Mistake-prone** — did you (or could you reasonably) get it wrong?
3. **Multi-step / order-matters** — is it a checklist, not a one-liner?

If any one says yes → capture it now. If all three say no → keep watching,
no skill yet. Prevents skill spam, catches the high-value ones early.

Format: see ~/.claude/skills/<any>/SKILL.md for the frontmatter spec.
```

Empty otherwise. KISS. If `.claude/skills/` already exists, leave it alone.

### Step 6 — Ensure global SessionStart context hook (idempotent, no prompt)

Detect whether `session-context.sh` is **specifically** registered in `~/.claude/settings.json` under `hooks.SessionStart` (not just "any SessionStart hook"). If registered: skip silently, note in report.

If NOT registered: install silently — by the time the user invokes `/claudify` they've opted into the bootstrap; a separate gate breaks autonomous mode.

1. Write `~/.claude/hooks/session-context.sh` (mode 0755) if absent.
2. Append a single entry to `hooks.SessionStart[0].hooks` (preserve existing entries — never overwrite).
3. Validate the patched JSON parses; if not, abort and report — never leave it broken.

To undo (document in report): remove the entry and delete `~/.claude/hooks/session-context.sh`.

Proposed hook (`~/.claude/hooks/session-context.sh`):

```bash
#!/usr/bin/env bash
# Inject lightweight per-session context — free tokens, deterministic.

if ! git rev-parse --git-dir > /dev/null 2>&1; then
  exit 0
fi

echo "[branch] $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"

status=$(git status --short 2>/dev/null | head -20)
if [ -n "$status" ]; then
  echo "[status]"
  echo "$status"
fi

echo "[recent commits]"
git log --oneline -5 2>/dev/null
```

Settings patch (merge into existing `hooks` block — never overwrite other hooks):

```json
{ "hooks": { "SessionStart": [ { "command": "~/.claude/hooks/session-context.sh" } ] } }
```

If other `SessionStart` entries exist, APPEND — never replace.

---

# Phase 2 — DEEP INDEXABILITY (when earned)

Set the repo up so any future AI session cold-starts in <2k tokens and knows exactly where to look. A disciplined pass that ships a known-good set of navigation artifacts + the audit guardrails that keep them honest.

The pattern this enforces — a repo is "AI-indexable" when these exist and stay in sync:

1. `CLAUDE.md` has a "Where to look" nav table at the top — the single entry point.
2. `docs/CODE_MAP.md` — one-page index: file tree, concept→file lookup, file sizes (token budget), section-marker grep hints.
3. `docs/LESSONS.md` — anti-repeat list. Every binding rule cites the **commit hash** that established it. `git show <hash>` is the source of truth.
4. `docs/API-QUIRKS.md` — service-by-service gotchas (omit if no external APIs). Same commit-hash provenance.
5. `scripts/README.md` — manifest of every script (omit if no `scripts/`).

Plus guardrails: `make audit-docs` (every cited hash resolves, every doc link exists) and `make ai-brief` (prints the cold-start brief). The **commit-hash provenance trail is the load-bearing piece** — memory rots, `git show <hash>` doesn't.

### Step 0 — Maturity gate (decides whether Phase 2 runs)

- **`/claudify floor`** → skip Phase 2 entirely. Note "indexability skipped (floor mode)" in the report. Done.
- **`/claudify deep`** → force Phase 2 even if borderline.
- **`/claudify` (bare)** → run Phase 2 ONLY if the repo is mature. Bail (and note "indexability deferred — repo not mature yet") if ANY:
  - < ~10 commits or first commit < ~2 days old (no institutional knowledge yet),
  - toy / experiment / mock (the docs would outweigh the code),
  - the nav docs already exist and are current (run `make audit-docs` first if present).

  Use the Phase-1 survey's maturity signals to decide. In autonomous mode, decide and ship: ≥10 commits AND not obviously a toy → proceed. Document the call in the report.

### Step A — Build `docs/CODE_MAP.md`

The single most valuable artifact. One page:

```markdown
# Code map
Single-page index. Read this once per session.
## Tree
[ASCII tree of source files with a one-line purpose per file]
## Find by concept
| If you want to touch … | Open … |
|------------------------|--------|
| [concept]              | `path/to/file.go::Symbol` |
## File sizes (token budget)
| File | Lines | Read in full? |
## Section markers inside long files
[bash grep snippet for any `// ─── ` or equivalent markers]
## Conventions
[any cross-cutting rules — idempotency, comment policy, etc.]
```

Build it from the actual file list (don't invent files); glance at each long file's top + section markers for the one-liner; pick ~10 of the most common navigation questions for the concept table.

### Step B — Build `docs/LESSONS.md`

Mine `git log` for `fix:` commits and bug-flavored fixes. For each lesson worth capturing:

```markdown
### [Short rule, imperative]
- **Why:** [the incident in one or two sentences].
- **Provenance:** `<7-char-hash> <commit subject>`
```

If the repo is too new for a track record, write the template + a single seeding rule for conventions discovered, marked as a starter. **Verify every hash with `git cat-file -e <hash>` before saving** — bad hashes are worse than none.

### Step C — Build `docs/API-QUIRKS.md` (only if external APIs exist)

One H2 per service:

```markdown
## ServiceName (vX)
### [Quirk title]
- **Detail:** [the thing to know]
- **Provenance:** `<hash> <subject>`
```

Skip the file entirely if no external API surface. Don't fabricate quirks.

### Step D — Build `scripts/README.md` (only if `scripts/` exists)

Read every script header (first 5–10 lines). Build a table:

```markdown
| Script | Make target | One-line purpose | Idempotent? | When to run |
```

If a script has no Makefile target, surface it — the user may want to add one.

### Step E — Add the "Where to look" nav table to `CLAUDE.md`

Lead with it near the top, BELOW any "must read first" preamble the user wrote. Existing binding rules stay; the nav table is purely additive. Omit rows for docs that don't exist.

```markdown
## ⚡ Where to look (start every session here)

| Looking for …                            | Open …               |
|------------------------------------------|----------------------|
| **Where any file/symbol/concept lives**  | `docs/CODE_MAP.md`   |
| **API gotchas** (per service)            | `docs/API-QUIRKS.md` |
| **Things this repo has gotten wrong**    | `docs/LESSONS.md`    |
| **What does script X do, when to run it?** | `scripts/README.md`|
```

### Step F — Wire `make audit-docs` + `make ai-brief`

If the repo has a `Makefile`, append both targets. If not, drop them as `scripts/audit-docs.sh` + `scripts/ai-brief.sh`.

```make
audit-docs:
	@bad=0; \
	for h in $$(grep -hoE '`[a-f0-9]{7,40}`' docs/LESSONS.md docs/API-QUIRKS.md 2>/dev/null | tr -d '`' | sort -u); do \
	    git cat-file -e $$h 2>/dev/null || { echo "BAD HASH: $$h"; bad=1; }; \
	done; \
	for l in $$(grep -hoE '\]\([^)]+\.md[^)]*\)' docs/*.md CLAUDE.md 2>/dev/null | sed -E 's/.*\(([^)]+)\)/\1/' | cut -d# -f1 | sort -u); do \
	    [ -f "$$l" ] || { echo "BAD LINK: $$l"; bad=1; }; \
	done; \
	test $$bad -eq 0 && echo "audit-docs: OK"

ai-brief:
	@echo "═══ CODE MAP ═══"; head -40 docs/CODE_MAP.md 2>/dev/null
	@echo; echo "═══ RECENT LESSONS ═══"; grep -E '^### ' docs/LESSONS.md 2>/dev/null | head -10
	@echo; echo "═══ LAST 10 COMMITS ═══"; git log --oneline -10
	@echo; echo "═══ TODO / FIXME (top 5) ═══"; grep -rnE 'TODO|FIXME' --include='*.go' --include='*.py' --include='*.ts' --include='*.js' . 2>/dev/null | head -5
```

(Adjust grep globs to the repo's languages.)

### Step G — Green checkpoint (Phase 2)

Run `make audit-docs` (or the bash equivalent). MUST pass before committing. If the repo has tests/lint/format/typecheck, run them — touching only markdown shouldn't break anything, but verify.

---

## Commit

Only if a git repo. Stage ONLY what claudify created or updated:

- Floor: `CLAUDE.md`, `.claude/skills/README.md` (if newly created).
- Deep (if Phase 2 ran): also `docs/CODE_MAP.md`, `docs/LESSONS.md`, `docs/API-QUIRKS.md`, `scripts/README.md`, `Makefile` / `scripts/*.sh` — whichever were written.

Commit message:
- Floor only: `chore: claudify (Claude Code bootstrap)`
- Floor + deep: `chore: claudify — bootstrap + AI-indexability pass`

Do NOT stage unrelated files. Do NOT amend. If not a git repo, skip and note in the report.

## Final report (mandatory)

```
Claudified <repo path>.

  CLAUDE.md       <created|updated|unchanged>  (<n> lines, target ≤80 + nav table)
  .claude/skills  <created|already present>
  SessionStart    <installed globally|already present|skipped by user>
  Indexability    <ran|deferred: not mature|skipped: floor mode>
    CODE_MAP      <created|updated|n/a>
    LESSONS       <created|updated|n/a>
    API-QUIRKS    <created|n/a (no external APIs)>
    scripts/README <created|n/a (no scripts/)>
    audit-docs    <OK|n/a>
  Commit          <short SHA|skipped (not a git repo)>

Next session in this repo:
  - CLAUDE.md auto-loads (~<n> lines fixed cost) + nav table for on-demand lookup
  - SessionStart injects branch + status + last 5 commits (zero LLM tokens)
  - make ai-brief prints the cold-start brief    (if deep ran)
```

The diff has the details; the report is for orientation. If Phase 2 was deferred/skipped, say why in one line and note the next session can run `/claudify deep`.

**Mock-backend gap (report it, never auto-add it).** If survey Q7 found a frontend that calls an API with no contract and/or no mock layer, close the report with ONE line naming exactly what's missing and what it costs — e.g. *"`web/` calls the API with no OpenAPI contract and no MSW layer: every feature is blocked on the backend, and frontend tests re-fixture responses by hand."* Then offer to add it. Do NOT install `msw` or write handlers as part of claudify — claudify makes a repo legible, it does not restructure it; adopting a mock backend is a real change the user opts into. (Rules: the `mock-backend` rule-card.)

## Idempotency rules

- **Always read before writing.** Existing `CODE_MAP.md` → augment vs rewrite (rewrite if sparse, merge if substantial).
- **`docs/LESSONS.md` is append-only.** Never delete entries.
- **The CLAUDE.md nav table** goes near the top but BELOW any "must read first" preamble. Don't bury what's there.
- **Don't fabricate.** No invented commit hashes, quirks, or file paths. The whole value is grounded-in-reality navigation.

## Hard anti-patterns

- ❌ Don't paste file or function bodies into `CLAUDE.md`.
- ❌ Don't preemptively fill `.claude/skills/` with speculative skills.
- ❌ Don't overwrite a hand-written `CLAUDE.md` without merging/showing the diff.
- ❌ Don't `git init` silently.
- ❌ Don't stage unrelated files in the commit.
- ❌ Don't add CI, husky, lint-staged, pre-commit framework — out of scope.
- ❌ Don't run Phase 2 on a toy/new repo. The maturity gate is non-negotiable; doc noise on an immature repo is worse than no docs.
- ❌ Don't fabricate CODE_MAP entries or LESSONS hashes to look thorough.

## When NOT to use

- Scaffolding a brand-new empty project → use `scaffold` first, then `claudify`.
- Adding one new skill to an already-claudified repo → just write the skill.
- Making non-bootstrap changes to a repo → normal incremental work.
