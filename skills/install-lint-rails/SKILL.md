---
name: install-lint-rails
description: Install the mechanical enforcement layer for sloppy-AI patterns into any mature project — universal checks + stack-detected packs + domain-opt-in packs, wired into pre-commit and the green gate. Trigger phrases include "/install-lint-rails", "install lint rails", "set up the anti-pattern gate", "wire pre-commit lint checks", "make the codebase enforce its rules", "stop you from cheating", "close the escape hatches mechanically". Use AFTER /claudify on mature repos. Do NOT use on toy / experimental / sub-day-old repos — the checks have to earn their keep. Idempotent; re-running updates only what changed.
---

# Install lint rails

Install the mechanical enforcement layer for sloppy-AI patterns into any
mature project. Three layers: universal checks (always applied) +
stack-detected packs (auto-applied based on manifest detection) +
domain-opt-in packs (user-asked).

## When to use

Trigger phrases: `/install-lint-rails`, "install lint rails",
"set up the anti-pattern gate in this repo", "wire pre-commit lint
checks", "make the codebase enforce its rules".

Use AFTER `/claudify` — its Phase 2 (deep, on mature repos) scaffolds
CODE_MAP / LESSONS / API-QUIRKS, which the drift checks build on.
The two skills layer:

- `/claudify` — FLOOR (any repo) + navigation layer (Phase 2, mature repos: CODE_MAP / LESSONS / API-QUIRKS). Subsumes the former `/ai-indexability`.
- `/install-lint-rails` — enforcement layer (mature repos where regressions cost time).

Do NOT use on toy / experimental / sub-day-old repos. The lint scripts
have to earn their keep; on a 3-file experiment they're noise.

Idempotent: re-running detects existing scripts and updates only what
changed. Won't overwrite project-local edits to copied check files.

## Inputs

The skill reads (does not modify) these project files to decide what
to install:

- `package.json` (root + `tests/`) — JS / TS, Playwright detection
- `pyproject.toml`, `setup.py`, `requirements.txt` — Python detection
- `go.mod` — Go detection
- `Cargo.toml` — Rust detection
- `Gemfile` — Ruby detection
- Existing `scripts/lint-anti-patterns.sh` — idempotency probe
- Existing `Makefile` — adds targets if missing, never overwrites

## Procedure

### Step 1 — Detect state (read-only, no writes)

Report in one line BEFORE touching anything:

- Is this a git repo? (`git rev-parse --git-dir`)
- Does `scripts/lint-anti-patterns.sh` exist? → idempotent update or fresh install.
- Does `Makefile` exist? → preserve user targets, add lint/verify if missing.
- Does `.git/hooks/pre-commit` exist (or `scripts/pre-commit`)? → wire vs replace.
- Manifest detection: enumerate matched stacks.

If not a git repo: tell the user. The growth check and pre-commit hook
need git; offer to proceed with the non-git checks only.

If the project is < 10 commits or < 2 days old: tell the user this skill
adds infrastructure they may not need yet. Ask before proceeding.

### Step 2 — Survey stacks

Run these checks (each is one cheap fs probe). Match → add the pack.

| Pack | Detect via | Substring (optional) |
|---|---|---|
| `universal` | always | — |
| `stack-conformance` | always (each check self-gates by file presence) | — |
| `playwright` | `package.json` exists | `@playwright/test` |
| `python` | `pyproject.toml` OR `*.py` at root OR `src/**/*.py` | — |
| `node` | `package.json` exists | — |
| `go` | `go.mod` | — |
| `rust` | `Cargo.toml` | — |
| `shell` | `scripts/*.sh` OR root `*.sh` | — |

Multiple packs can apply (a JS+Python repo gets both `node` + `python`).

### Step 3 — Ask the domain question (ONE question, four options)

Use `AskUserQuestion` with:

> "Any domain-specific concerns for this repo's lint rails?"
>
> 1. **Data-loss surface** — file mutations, photo/document libraries, anything where a bug means irreversible data loss.
> 2. **Security-critical** — auth flows, secret handling, public-internet exposure.
> 3. **Public-API stability** — a library others depend on; breaking-change detection matters.
> 4. **None of the above** — internal tools, dev infrastructure, scripts.

Only one selection. Domain packs (if you build them later) layer on top.
For v1 there's no domain pack — this question primes future expansion.

### Step 4 — Install packs

For each matched pack:

1. Create `scripts/lint-checks/` if missing.
2. **COPY** each check file from `~/.claude/lint-checks-library/<pack>/`
   into `scripts/lint-checks/`. Use the `cp -n` idiom — never overwrite
   an existing project-local file (the user may have tuned it).
3. `chmod +x` for shell scripts; Python ones stay 0644.
4. Note the `severity` (fail/warn) and `needs` (preconditions) from the
   pack's `pack.toml` for the orchestrator.
5. **Record the source version** in the manifest
   `scripts/lint-checks/.installed-versions` — one `<sha256>␉<filename>` line
   per file copied (the hash of the LIBRARY file you copied from). This is what
   makes Step 4a able to tell a stale copy from a locally-tuned one. On a fresh
   copy, write/replace that file's line with the current library hash.

### Step 4a — Refresh stale copies (idempotent self-update)

`cp -n` protects local edits but means a LIBRARY BUGFIX never reaches a repo
that already has the old copy. This step closes that gap — refresh unmodified
copies, never clobber edited ones. On a re-run, for every already-present check,
compute three hashes (`shasum`/`sha256sum`): `proj` (project copy now), `lib`
(current library version), `installed` (the manifest line, if any). Then:

| proj vs lib | proj vs installed | Action |
|---|---|---|
| equal | — | up to date — skip |
| differ | `proj == installed` (untouched since install) | **REFRESH**: copy library→project, update manifest line. Library fix propagates. |
| differ | `proj != installed` (locally edited) | **KEEP** the project copy; report "locally modified, library differs — review" + show the diff. Never clobber. |
| differ | no manifest line (pre-manifest install) | Decide DETERMINISTICALLY — see below. Do NOT eyeball-guess (two runs of this skill MUST reach the same verdict on the same files). |

**No-manifest verdict — deterministic, not judgment (these check files are
LIBRARY-OWNED; the library is the source of truth):**

1. `diff -bw proj lib` (ignore ALL whitespace) is **empty** → the only drift is
   formatting (e.g. the repo ran `shfmt` over the checks). That is NOT a local
   edit → **REFRESH** + backfill manifest.
2. **Severity is never a reason to KEEP.** `warn`/`fail` lives in the orchestrator's
   `run_check` line, NOT in the check file — refreshing file content can't change
   it. "It's tuned to warn mode" is not file drift.
3. `diff -bw` **non-empty** → real content drift. **Default = REFRESH** (the repo
   is behind on an upstream fix — that's stale, not edited). **KEEP only** if you
   can NAME a concrete project-local customization present in the project copy that
   the library lacks (a tuned threshold/regex/path) — then report it and skip. Being
   *behind* the library is never a keep reason.

**Do NOT reformat refreshed checks** — keep the library's exact bytes, and make
sure the repo's own formatter does NOT cover `scripts/lint-checks/` (add an ignore
if it does). The hash manifest depends on each project copy staying byte-equal to
the library version it came from; running `shfmt` over them re-introduces
whitespace drift and makes the next run mis-read a stale copy as "locally edited"
(the exact bug that split the two sibling projects' verdicts). The only formatters
that touch the checks dir are `shfmt` (shell) and `ruff` (python) — Biome handles
JS/TS/CSS/JSON elsewhere and never touches these. Then backfill the
manifest for every refreshed file. (Worked example: a repo whose checks were
`shfmt`-reformatted to tabs and were behind on upstream fixes, with no
project-specific logic → ALL refresh to library bytes, none kept, formatter scoped
to exclude the checks dir.)

**Do the refresh as ONE atomic shell call** — `cp` every stale file → library,
rebuild the manifest, `git add scripts/lint-checks/`, AND `git commit`, all in a
single invocation. Do NOT split the `cp` from the `git add`/commit across separate
tool calls: in a sandboxed shell, file writes may not persist between calls, which
silently commits the manifest while leaving the `.sh` bodies stale (a partial,
inconsistent commit — this cost a real run two commits + 6 min to untangle).
**Post-condition (verify, don't assume):** after committing, confirm
`git show HEAD:<check>` is byte-equal to the library for every refreshed file. Any
mismatch = the write didn't land → redo the whole transaction in one call.

Report a one-line tally: `refreshed N · kept-modified M · reviewed K`. Refreshing
is content-only — it does NOT change a check's installed severity (that stays
whatever the orchestrator's `run_check` line says, governed by Step 5a).

### Step 5 — Generate the orchestrator

If `scripts/lint-anti-patterns.sh` doesn't exist: copy the template from
`~/.claude/lint-checks-library/_template/lint-anti-patterns.sh` and
substitute the `{{CHECKS_BLOCK}}` placeholder with one `run_check`
line per installed check.

If it DOES exist: parse its existing `run_check` lines, add any new ones for the
just-installed packs, and **re-assert every line at its `pack.toml` severity**
(an older install may have downgraded some to `warn` — restore them to `fail`;
downgrades are banned, see Step 5a). **Strip any legacy `# TODO(lint):` /
`# FLIP-WHEN-CLEAN(lint):` markers** — they were artifacts of the dead downgrade
flow (and `TODO` self-trips `todo_without_ref`). Print the diff before saving.

Each `run_check` line is:
```
run_check "TITLE" path/to/check.{sh,py} {fail|warn}
```
TITLE = a short human-readable section name. Auto-generate from the
filename if you want consistency (`no_wait_timeout.sh` → "no_wait_timeout"
displayed as `no wait timeout`).

If a check has `needs = "<path>"` in its pack.toml AND that path doesn't
exist in the project, SKIP installing it. (Example: codemap_drift.py
needs `docs/CODE_MAP.md`. If absent, skip — the project hasn't run
`/claudify deep` (Phase 2) yet.)

#### Step 5a — Existing-codebase rollout: report, then INSTALL AT FULL SEVERITY

**No downgrades. Ever.** A check installs at its `pack.toml` severity — a `fail`
check is `fail`, even on a repo that already violates it. Downgrading `fail`→`warn`
because a repo is dirty is an ESCAPE HATCH: it ships KNOWN violations green and
silently ACCEPTS off-stack code (e.g. SvelteKit slipping past `frontend_framework`).
Banned, same as the `*-OK` comments.

1. **Report first (read-only).** Dry-run every to-be-installed check and print a
   per-check inventory: `check · pre-existing findings · severity`. So the user sees
   exactly what will block — no surprises, but no softening either.
2. **Install at pack severity, period.** Every check goes in at its real severity.
   If the repo is messy or OFF-STACK, the gate is RED until it conforms — that is the
   point, not a bug. Off-stack frameworks (SvelteKit / Next / CRA) hard-fail
   `frontend_framework`: the fix is to MIGRATE to the stack (Vite + React), never to
   accommodate the deviation. The tool does not bend to a repo's existing choices —
   the user's stack wins, and a repo that disagrees is non-conformant until migrated.
3. **Hand back a FIX plan, not a hatch.** List what's red and how to clear it
   (`/ui-conform` for UI/scale; migrate off-stack frameworks; fix Go/test findings).
   No warn-purgatory, no escape comment, no "flip later" — red means fix it (or make
   a deliberate, explicit migration decision), then commit.

A staged migration of a large legacy repo is a conscious decision the USER names out
loud — it is never a default the tool grants itself by quietly downgrading.

### Step 6 — Wire pre-commit

If `scripts/pre-commit` doesn't exist: copy the template and substitute
`{{TEST_COMMAND_BLOCK}}` based on detected stack:

| Stack | Substitution |
|---|---|
| `playwright` | `cd "$ROOT/tests" && npm test --silent` |
| `python` (pytest) | `cd "$ROOT" && pytest -q` |
| `node` (no playwright) | `cd "$ROOT" && npm test --silent` |
| `go` | `cd "$ROOT" && go test ./...` |
| `rust` | `cd "$ROOT" && cargo test --quiet` |
| `ruby` | `cd "$ROOT" && bundle exec rake test` |
| none detected | Leave the placeholder + note for the user. |

If `scripts/pre-commit` exists: check whether it already calls
`lint-anti-patterns.sh`. If not, prepend the lint gate (Gate 1) before
the existing test gate (Gate 2). Show the diff first.

Install the hook symlink:
```bash
ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
```
(Only if `.git/hooks/pre-commit` doesn't already exist or points
elsewhere — ask first if there's a conflict.)

### Step 7 — Generate / update the Makefile

If no `Makefile`: copy the template, substitute the test target based
on detected stack (same table as Step 6).

If a `Makefile` exists: check for `lint`, `test`, `verify` targets.
Add the missing ones at the top of the file. Never overwrite existing
targets.

### Step 8 — Smoke-test

Run `bash scripts/lint-anti-patterns.sh` in the project. If it exits 0
or with only warnings, the install is clean. If hard failures fire,
they were ALREADY present — the new gate caught them. Report the
findings to the user; do NOT auto-fix.

### Step 9 — Final report

Print exactly this:

```
Installed lint rails in <repo path>.

  Packs installed:        <list>
  Checks total:           <count> (<n> hard-block, <m> warn)
  Pre-commit:             <wired|already wired|conflict — see above>
  Makefile:               <created|targets added|unchanged>
  First run:              <PASS|N findings — see above>

  Bypass any individual check by editing scripts/lint-checks/<file>.
  Re-run any time:        make lint
  Full gate:              make verify
```

## Idempotency rules

- COPY check files via `cp -n` (no-clobber). User edits to copied
  files are sacred.
- Re-run scans all packs and adds only NEW check files / NEW
  orchestrator lines — AND refreshes stale UNMODIFIED copies with the
  latest library version (Step 4a, manifest-gated). So a library bugfix
  reaches existing installs on the next re-run without clobbering local edits.
- Never re-write `scripts/pre-commit` if it already calls
  `lint-anti-patterns.sh` — that means it's already wired.
- Never overwrite Makefile targets that already exist.

## Anti-patterns

- ❌ Don't run on repos < 10 commits without asking first.
- ❌ Don't symlink check files from the global library — projects must
  be self-contained (copy, not link).
- ❌ Don't generate inline Python in the orchestrator script via heredocs
  — call the standalone files in `scripts/lint-checks/` instead. (Bash's
  `$(...)` parser chokes on Python regex paren-balance otherwise.)
- ❌ Don't add a check that has known false positives without an escape
  marker. Every check ships with one.
- ❌ Don't touch the user's global `~/.claude/CLAUDE.md`. The "every
  project that earns `/claudify deep` also earns /install-lint-rails"
  rule lands via `/sharpen` invoked by the user.

## Extending the library

To add a new check pack (new language, new framework):

1. Create `~/.claude/lint-checks-library/<pack-name>/`.
2. Add `pack.toml` with name, version, applies_when condition, and
   `[[checks]]` entries.
3. Add the check files (`.sh` or `.py`). Each:
   - Exits 0 on clean, 1 on hard violation.
   - Prints findings to stdout as `file:line: message`.
   - Has NO escape/bypass marker — the `no_escape_comments` lock bans all
     `*-OK` comments, so a check must never offer one. Findings get fixed.
   - Bounded scope (uses `git ls-files` rather than recursive walks).
4. Next time `/install-lint-rails` runs in a matching project, the
   pack auto-installs.

To add a check to an existing pack: drop the file in the pack dir,
add an entry in `pack.toml`. Idempotent re-run picks it up.

## What this CAN'T fix

- Architectural drift across many commits. Single-commit checks miss
  slow accretion.
- Subtle correctness bugs (race conditions, off-by-one). Still needs
  review.
- New frameworks. The library needs maintenance as the ecosystem
  evolves. There's no auto-update; you add packs as you encounter
  the patterns worth catching.

## See also

- `~/.claude/lint-checks-library/` — the packs.
- `/claudify` — its Phase 2 (deep) pairs with this skill (CODE_MAP enables the
  drift check). Subsumes the former `/ai-indexability`.
- `/sharpen` — for locking in new project-local rules (subsumes the
  former `/ingrain`). When you lock in a rule that could be mechanically
  enforced, ALSO add a check to the relevant pack.
