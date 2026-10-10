---
name: ui-conform
description: Use to migrate an EXISTING UI onto the stack (Tailwind + shadcn + a named scale) WITHOUT changing how it looks — pixel-identical, verified by before/after screenshot diff. Trigger phrases include "/ui-conform", "conform the UI to the stack", "make the UI stack-compliant", "migrate to tailwind without changing the look", "keep the design but use shadcn", "move the CSS-in-JS to tailwind", "tokenize the design", "fix the spacing rhythm without a redesign". The look is PRESERVED. Do NOT use when you want a NEW/different design (that's /ui-overhaul, which is destructive) or a brand-new project (scaffold / ui-mocks).
---

# UI conform — migrate an existing design onto the stack, pixel-identical

Bring an already-built UI into compliance with the stack — Tailwind utilities + a named
scale, shadcn/Radix primitives, one token source, client+server form validation — while
**keeping exactly how it looks today**. This is a refactor/migration, NOT a redesign.

## This is the OPPOSITE of /ui-overhaul — read this first

`/ui-overhaul` deletes the old UI and builds a new look. **This skill must not change the
look at all.** Your job is invisible-to-the-eye: same pixels, better foundation.

- The bug to guard against here is the inverse of overhaul's: **"while I'm in here, let me
  improve this spacing / tweak this color / modernize this component."** STOP. Any visible
  change is a defect in this skill. Improvements are a SEPARATE, later, explicit task.
- NEVER demolish, archive, generate mock directions, or open `frontend-design` for a new
  thesis. The existing design IS the spec. If the user wants a new look, this is the wrong
  skill — point them at `/ui-overhaul`.
- The proof of success is a screenshot diff that shows **no visual change** while the code
  underneath moved onto the stack.

## Step 0 — Confirm intent + lock rollback

1. Confirm in writing: "Keep the current look exactly, migrate the code onto the stack — no
   visual change. Correct?" If they actually want it to look *better/different* → STOP, use
   `/ui-overhaul`.
2. Confirm a clean git ref exists (`git status` clean, else commit/stash). Print the rollback hash.
3. Confirm the stack applies: React + Tailwind target. If the app is React-but-not-Tailwind,
   adding Tailwind is part of the migration. If it's not React at all, this skill doesn't apply.

## Step 1 — Baseline screenshots (the ground truth)

Before touching ANY code, capture the current look as the diff baseline. This is what every
later step is checked against.

- Set up Playwright if absent. On homeserver, screenshots run via the ephemeral docker image — see
  the `playwright-docker` rule (NEVER native chromium). Mac: `bunx playwright`.
- For every page/route, capture at **375×667 and 1280×800 × light + dark** (disable
  animations, wait for fonts/`networkidle`, stub random/time content for determinism).
- Save as `tests/visual.spec.ts-snapshots/` baselines and COMMIT them: `test: baseline
  pre-conform screenshots`. These are the contract: every conform pass must diff clean
  against them (`toHaveScreenshot({ maxDiffPixelRatio: 0.01 })`).

## Step 2 — Audit (read-only)

1. Run `/install-lint-rails` in **report mode** (Step 5a there) — the violation inventory is
   your worklist: every inline style / CSS-in-JS, raw color, off-scale value, native
   `<select>` / hand-rolled modal, unvalidated handler. Install dirty blockers as `warn` for now.
2. Inventory the de-facto design values actually in use: the real palette, the real spacing
   numbers, the real type sizes/line-heights/tracking, radii, shadows, motion. THESE become
   the scale — you are naming what already exists, not inventing new values.

## Step 3 — Establish the scale FROM the existing look (zero pixel change)

Codify the audited values into the stack's single source, choosing the actual current
numbers so nothing moves visually:

- `tailwind.config`: `theme.extend.{spacing, fontSize (as [size,{lineHeight,letterSpacing}]),
  letterSpacing, borderRadius, boxShadow, transitionTimingFunction}` set to the values the UI
  already uses. Prefer SEMANTIC keys (`text-title`, `gap-section`) mapped to today's pixels.
- Colors → CSS custom props in ONE global sheet (`src/index.css` `:root` + `[data-theme]`),
  values = the current palette, referenced by the Tailwind theme. Kill any second/dead token
  system (this is where `single_token_source` earns its keep). See `[rule:ui-scale]`.
- Commit: `refactor(ui): name the existing design as the Tailwind scale (no pixel change)`.

## Step 4 — Migrate in pixel-identical passes (exemplar first, then sweep)

Do ONE representative screen end-to-end first; screenshot-diff it clean against the baseline;
THEN sweep the rest the same way. Each pass is its own commit, each verified visually:

1. **Tokenize pass** — replace raw literals with the scale tokens you just defined
   (`#2f6f5b`→`text-acc`, `13px`→`text-title`, `p-[16px]`→`p-4`). Pure rename. Diff MUST be
   clean (identical pixels). This is the safest, biggest pass.
2. **CSS-in-JS → Tailwind utilities** — move `<style>{CSS}` / `style={{}}` into utility
   classes (resolving through the tokens). Diff clean.
3. **Bespoke primitives → shadcn** — native `<select>` → shadcn Select, custom modal/overlay
   → shadcn Dialog, etc. Restyle each shadcn component with your tokens so it matches the old
   one pixel-for-pixel (this is where you adopt the solved focus-trap/a11y you were missing —
   the only *invisible* improvement allowed). Diff clean (visually; a11y improves underneath).
4. **Forms → AppForm + validation** — hand-rolled `<form>` → `AppForm`/rhf+zod; add the
   missing server-side validation (Go handler rejects bad input). Visible form layout
   unchanged; the disabled/loading/error UX is added where it was missing (that IS a
   behavior improvement, call it out — it's the point of conforming forms).

After each pass: run the screenshot diff. **Any visual delta = a mistake in that pass — fix
until identical** (or, if a delta is an unavoidable consequence of a primitive swap, surface
it to the user and get explicit sign-off before continuing).

## Step 5 — Lock it

1. Flip the `warn`'d structural checks to `fail` (`/install-lint-rails` again, or edit the
   `run_check` severity) now that the repo is clean — drift can't return.
2. Keep the visual-regression spec from Step 1 as the standing guard; intentional future
   design changes update the baseline in a separate, titled commit.
3. Final report: the before/after screenshots side by side (proving NO visual change), the
   lint inventory now at zero, and the list of invisible wins (tokens unified, a11y gained on
   primitives, forms validated both sides).

## Verify, then report (mandatory)

Before claiming done, show in the conversation:
- **Screenshot diff: baseline vs now = clean** at 375/1280 × light/dark for each page. If any
  page differs visibly and it wasn't explicitly signed off, it's NOT done.
- **Lint inventory at zero** (the checks that were `warn` now pass as `fail`).
- **Diff stat** of the migration commits.

If the look changed without sign-off, the conform FAILED — say so and fix. The words "done"/
"complete" are banned until the clean screenshot diff is on screen.

## See also

- `/ui-overhaul` — the destructive sibling: NEW look, demolish + rebuild. Use that when the
  design should change.
- `/install-lint-rails` — installs/locks the gates this skill cleans the repo for.
- `[rule:ui-scale]`, `[rule:ui-adopt-dont-reinvent]` — the contract being conformed to.
- `playwright-docker` rule — how screenshots run on homeserver.
