---
name: ui-overhaul
description: Use when the user wants to COMPLETELY overhaul, redesign, rebuild, or replace an existing project's UI. Trigger phrases include "overhaul the UI", "redesign from scratch", "rebuild the UI", "throw away the design", "scrap and rebuild", "fresh start for the UI". Mocks are served INSIDE the app behind a single flag at the app's OWN single URL — never a separate server/port/DNS. Do NOT use for incremental UI changes, polish, bug fixes, styling tweaks, or new features added within the existing design language — those are normal UI work.
---

# UI overhaul

Total replacement of an existing project's UI. The layer below the UI (data models, API, business logic, auth) stays intact unless the user explicitly says otherwise.

> **Wrong skill if you want to KEEP the current look.** This is DESTRUCTIVE — it throws the
> design away and builds a new one. To keep the existing design and only make it
> stack-compliant (CSS-in-JS→Tailwind, raw values→scale, bespoke→shadcn), pixel-identical,
> use **`/ui-conform`** instead. Confirm the user actually wants a *new look* before proceeding.

## Read this before starting

Your default behavior is to match existing patterns and ship the smallest diff. **Here, that default is WRONG.** Your job in an overhaul is to delete and replace, not to preserve and improve.

Past failure modes this skill exists to prevent:

- Generating the mocks, then making small tweaks to the existing UI instead of actually replacing it.
- Preserving the old UI's patterns, naming, or file structure out of "respect for the codebase" when the user explicitly asked to throw them out.
- Claiming "overhaul complete" without actually replacing anything.

If at any point during this skill you catch yourself thinking *"let me keep this part of the old UI for consistency"* — **STOP.** That instinct is the bug. The user chose overhaul because the old way was wrong for them.

## Step 1: Lock the contract

Before any code, get explicit written agreement from the user on FOUR things. Read each back to them and get a confirmation in the conversation.

1. **Scope.** Run `git ls-files` and grep to enumerate every file/directory that constitutes "the existing UI". Read the full list back to the user verbatim. Ask: "Is this everything we're replacing? Anything I missed? Anything in this list that should actually stay?"
2. **Definition of done.** What does the overhauled UI ship with? Every page, route, component, flow. Same features as today? Pared down? Plus new? Get the answer in writing in the conversation — this becomes the inventory checked in Step 5.
3. **What stays.** Explicitly name what should NOT be replaced (data models, API layer, business logic, auth, routing config, build pipeline, etc.). Default assumption: only the UI layer changes; everything beneath stays. Confirm with the user.
4. **Rollback.** Confirm a clean git ref exists at the starting state. If the working tree is dirty (`git status` shows uncommitted changes), STOP and ask the user to commit or stash first. Print the commit hash you'd roll back to if this goes sideways.

Do NOT proceed past this step without all four locked. If the user pushes "just do it" — push back ONCE, explaining that this conversation is what prevents the past failure modes. Then proceed only if they confirm.

## Step 2: Mocks

Same generation procedure as the `ui-mocks` skill — and the SAME serving rule:
**mocks live IN the app behind one flag, at the app's OWN single URL. NEVER a
separate server/port/DNS.**

**Gate 1 — design thesis BEFORE any pixels (anti-templating).** For each of the 3
directions, first write a one-paragraph design thesis: the specific, unusual
concept driving it (grounded in THIS subject — its materials, vernacular,
artifacts), its signature element, its typography intent. A thesis like "clean,
modern, minimal" is a generic default — reject it and rewrite. Do NOT write mock
code until all 3 theses are concrete and distinct from each other. The old UI is
already demolished (Step 3 runs after pick, but you design as if it's gone — never
open it for reference; anchoring on it is what produces a re-skin).

- The 3 directions are routes in the app gated by ONE flag (`VITE_MOCKS=1` or the
  stack equivalent): `/mocks` (viewer/switcher) + `/mocks/01..03`. Flag off → not
  in the bundle. Do NOT create a standalone `mocks-ui/` static site.
- Each works end-to-end through a realistic full instance of the app's hardest real task. Real data, real microcopy, real states (loading, empty, error).
- Visually adventurous — the 3 must cover a wide range. Generic SaaS dashboard aesthetic for all 3 is a failure mode.
- **Apply the `frontend-design` skill's process to every direction** — this is where "best-in-class / wow" comes from, not optional: ground each in the subject, a deliberate design thesis, characterful typography, a signature element, intentional motion. If a direction reads like a generic template, redo it.
- **Every mock implements all three color modes** — auto (default, follows `prefers-color-scheme`), light, dark — with an in-mock toggle. Both light and dark must look finished, not afterthoughts. Non-negotiable.
- The viewer renders at `/mocks`: sidebar lists all 3, click to show, width control for mobile (375px) / tablet (768px) / desktop (1280px), global auto/light/dark toggle that drives all 3, keyboard nav, defaults to auto.
- **Additive routes, the real app stays up.** The flag ADDS `/mocks`; it does not replace the whole app.
- **View through what the user's browser can reach — for an edge app that's the edge, NOT a dev port.** Port-agnostic: on a locked-down / single-entry box (e.g. homeserver = `:443` only) ANY raw dev-server port — whatever the number — is firewall-blocked and unreachable no matter the host; the `block-mock-server` hook refuses side servers anyway. So BUILD with the flag and DEPLOY the container (`docker compose up -d --build`); the mocks are then at **`https://<app>.home.arpa/mocks`** (discover the name from the app's `caddy:` label) — same door, same SSO. Only on a plain box where the dev port is genuinely browser-reachable may you use the app's dev URL + `/mocks`.
- **Verify the URL the USER will open responds — from off-box, not `localhost`.** Curl the edge url, expect 200 or 302→SSO. A `200` on `localhost:5173` from the box proves nothing about the user's browser — that's the vapor that wastes their time.
**Gate 2 — independent distinctiveness critic BEFORE showing the user.** Don't grade your own work — self-grading is how a re-skin gets sold as "wow". Run a fresh-eyes critic (a subagent with NO context of how you built these) on each direction: *"Is this a distinctive, intentional design for THIS subject, or a generic template (default SaaS/dashboard, cream-serif, acid-accent-on-black, etc.)? Verdict + one reason."* Any direction it calls generic → redo or drop it. Only directions that survive the critic reach the user.

- **The 3 COMPETING mocks are CHEAP and come FIRST.** They are hardcoded-fixture views ONLY — no backend wiring, no feature build, no real data layer. Add them as lightweight routes to the existing app shell (or a minimal shell for a new project). **Do NOT build or wire the real application before the pick** — building the whole app before the user sees mocks wastes their time and is forbidden. (The *picked* direction DOES get a mock backend — see [Step 5](#step-5-mock-backend-picked-direction-only). Never build it for all three: two get deleted.)
- STOP after serving. Wait for "go with NN". Only AFTER the pick (Step 3) do you build and wire the real thing.

**Critical for overhaul:** the mocks must NOT borrow the old UI's design language, color palette, layout structure, or component patterns. The point is divergence. If a mock looks like a polish of the existing UI, redo it.

## Step 3: Demolish, then build

After the user says "go with NN":

1. **Demolish first — DELETE, don't archive.** `git rm -r` the entire old UI scope (every path enumerated in Step 1). Commit immediately: `chore: remove pre-overhaul UI (recoverable at <rollback-ref>)`, citing the Step 1 #4 rollback hash. Do NOT `git mv` it into an `.archive-pre-overhaul/` dir — git history already preserves it; an on-disk archive is dead-code litter that pollutes the tree and trips lint/search forever.
2. The old UI is now gone from the working tree. This is intentional — it prevents you from accidentally referencing or preserving its patterns while building the new one. Recovery, if ever needed, is `git show <rollback-ref>:path` or `git checkout <rollback-ref> -- path` — not a folder lying around.
3. **Make the chosen direction the real UI.** Take `/mocks/NN`, make it the app's default route(s), and DELETE the other two mock routes plus the `VITE_MOCKS` flag/gate (the chosen direction becomes the default, not a flagged route). Wire it to the real data layer, API calls, and business logic (the layer that stayed in Step 1 #3).
4. **Do NOT recreate the demolished UI's patterns, naming conventions, file structure, or component shapes.** The chosen mock is the new source of truth. Look at the mock; build from the mock.

If you find yourself running `git show <rollback-ref>:…` to "see how the old version did X" — STOP. The answer to "how should the new UI do X" is in the mock, not the old code. The only legitimate reason to pull from the old ref is to extract non-UI code (e.g., a data fetch helper that lived in the UI folder but isn't UI), and even then, copy the function, don't copy the patterns around it.

5. **Lock in the design system.** Before writing any new feature beyond the chosen mock, extract tokens + primitives + adherence rules. See the "Lock in the design system" section below.

## Step 4: Lock in the design system (after pick)

Lock the design language BEFORE any new feature work, so future sessions compose from it instead of inventing — the #1 cause of drift after mock-pick. **The HOW depends on the stack — pick the path; do NOT build a second token system next to one the stack already gives you.**

```
React + Tailwind in package.json?  →  Path A (default stack — reuse what's locked in globally)
vanilla / non-Tailwind web?        →  Path B (the CSS-custom-property approach)
```

### Path A — React + Tailwind (the default stack)

Do NOT create `ui/design-tokens.css`, a parallel `ui/components/`, a hand-written grep lint, or a `/* design-exception */` syntax. Those duplicate what the stack already enforces and become a stale second system (the exact drift this overhaul exists to kill). Instead:

1. **Tokens → `tailwind.config` + ONE global sheet.** Scrape the chosen mock's values and codify them as the project's scale: `theme.extend.{spacing, fontSize (as [size,{lineHeight,letterSpacing}] pairs), letterSpacing, borderRadius, boxShadow, transitionTimingFunction}` — your own values, not Tailwind defaults (that's where the mock's distinctiveness lives). Prefer SEMANTIC keys (`text-title`, `gap-section`). Colours go as CSS custom props in the ONE global sheet (`src/index.css` `:root` + `[data-theme="dark"]`), referenced by the Tailwind theme — one token source, one theme mechanism. (See `[rule:ui-scale]` / `[rule:ui-adopt-dont-reinvent]`.)
2. **Primitives → shadcn/ui.** The mock's recurring building blocks (Button, Card, Input, Dialog, Select…) are shadcn components — `bunx shadcn@latest add …` and restyle via tokens. You own the copied code. Never hand-roll a `<div role=dialog>` / native `<select>`. Forms use the `<AppForm>` primitive (rhf+zod+shadcn).
3. **Enforcement → `/install-lint-rails`.** Run it in the repo; the `stack-conformance` pack already blocks raw colours, off-scale type/spacing (`text-[13px]`), inline/CSS-in-JS, hand-rolled primitives, and >1 token source — with NO escape hatches (the `no_escape_comments` lock bans bypass comments; fix the code). Don't write a bespoke lint. Leave a one-line CLAUDE.md pointer: "UI composes from shadcn + the tailwind.config scale; gates enforced by stack-conformance."
4. **Migrating an inconsistent existing UI to the scale** (when sweeping the rest of the app onto the chosen direction, not just the promoted mock): **audit** de-facto type/spacing usage → **tokenize with ZERO pixel change first** (pure rename to scale tokens, screenshot-identical, checkpoint commit) → fix **one exemplar** screen end-to-end → **sweep** the rest against it → the lint gate keeps it from regressing. Tokenize before you restyle — never both in one diff.

Then go to **### 6 (visual regression baseline)** below — it applies to both paths.

### Path B — vanilla / non-Tailwind projects

For a project NOT on the React+Tailwind stack, the CSS-custom-property approach below is correct (there's no Tailwind theme to be the single scale). Do these five steps:

### 1. Extract design tokens → `ui/design-tokens.css`

Scrape the chosen mock's stylesheet. Pull repeated values into CSS variables under `:root` (light mode) and `[data-theme="dark"]` (dark mode):

- Colors: `--color-{bg,text,border,accent,muted,...}` for both modes
- Spacing scale: `--space-{1,2,3,...}` (typically a 4 or 8px grid)
- Type: `--text-{xs,sm,base,lg,xl,...}`, `--weight-{regular,medium,bold}`, `--leading-{tight,normal,relaxed}`
- Radii: `--radius-{sm,md,lg,full}`
- Shadows: `--shadow-{sm,md,lg,xl}`
- Motion: `--ease-{out,in,inout}`, `--duration-{fast,base,slow}`

For typed access in TS projects, also emit `ui/design-tokens.ts` re-exporting the same values.

### 2. Extract primitives → `ui/components/`

Identify the mock's recurring UI building blocks (Button, Card, Input, Modal, Badge, etc.). Build each as a primitive component that uses ONLY design tokens — no hardcoded values. Typically 5–10 primitives. Don't over-extract; add more as patterns repeat in real features.

### 3. Write design-adherence rules into project `CLAUDE.md`

Add (or create) a section in the project's `CLAUDE.md`:

```
## Design system (non-negotiable)

All UI work composes from `ui/components/` and `ui/design-tokens.css`. Never invent values.

- Colors: `var(--color-*)`. No raw hex/rgb/hsl in component code.
- Spacing: `var(--space-*)`. No raw px outside the tokens file.
- Type: `var(--text-*)`, `var(--weight-*)`. No raw font-size/weight.
- Primitives: every Button / Card / Input / Modal comes from `ui/components/`. Don't re-style ad-hoc.

Escape hatch: a one-off value needs `/* design-exception: <reason> */` on the line. The lint allows exceptions only with this comment.
```

### 4. Lint hardcoded values

Add a pre-commit lint rule that flags raw colors / spacings / type outside `design-tokens.css` and `ui/components/`. Mechanism depends on stack:

- Biome: custom regex rule in `biome.json`
- Stylelint: enable `color-no-hex` + `unit-disallowed-list` + `declaration-property-value-disallowed-list`
- Plain CSS: a `grep -rn -E '#[0-9a-fA-F]{3,8}|\b[0-9]+px\b' src/ ui/` check in pre-commit

Lines with `/* design-exception: <reason> */` pass.

The global `enforce-green-commit.py` PreToolUse hook will surface lint failures at commit time — drift becomes a red commit, not a slow rot.

### 5. Short `ui/README.md`

Three paragraphs: what's in `design-tokens.css`, how to add a new primitive (when the same ad-hoc pattern repeats 3 times in features, extract it), escape-hatch syntax.

### 6. Visual regression baseline

After 1–5, snapshot the chosen mock as the visual ground truth. Future drift then gets caught by diffing screenshots, not by hoping the model maintains discipline.

- **Set up Playwright** (skip if already installed):
  ```
  bun add -D @playwright/test
  bunx playwright install chromium
  ```
- **Baseline + regression in one spec** at `tests/visual.spec.ts`: for each page in `ui/`, capture at 3 viewports (375×667 / 768×1024 / 1280×800) × 2 color modes (light, dark) = 6 snapshots per page. Use Playwright's `toHaveScreenshot({ maxDiffPixelRatio: 0.01 })` — 1% pixel-diff tolerance covers sub-pixel rendering and anti-aliasing.
- **In every snapshot**: disable animations (`page.emulateMedia({ reducedMotion: 'reduce' })`), wait for `networkidle` + fonts loaded (`document.fonts.ready`), stub any random/time-based content so snapshots are deterministic.
- **Storage**: Playwright writes baselines to `tests/visual.spec.ts-snapshots/` by default; commit these. (For very large suites, consider git LFS.)
- **CI**: add `bun playwright test` to the project's test command. The existing `end-of-session-check.sh` TEST GATE hook ensures `feat:`/`fix:` commits touching UI run the suite.
- **Intentional design updates**: when the design legitimately changes (new accent, redesigned card), regenerate:
  ```
  bun playwright test --update-snapshots
  ```
  Commit the new baselines in a SEPARATE commit titled `chore: update design baseline — <reason>` so the change is auditable in git history.

After all six: token violations caught at commit (step 4), visual drift caught at CI (step 6). Belt + suspenders. Now build the mock backend.

## Step 5: Mock backend (picked direction only)

The picked mock is still a puppet — fixtures hardcoded per screen, no state carried between them. Before committing to the real backend, make the ONE chosen direction behave as if the whole app were built, so the user walks the complete flow and finds the design holes while they're still free to fix.

**Never for all 3 directions** — two get deleted; it's pure waste. Only after "go with NN".

Adopt **MSW** (`msw` v2 + `@mswjs/data`) — see the `mock-backend` rule-card for the rationale, the setup steps, and the handoff rule. It intercepts at the network layer (real `fetch` calls, no mock-aware app code) and runs INSIDE the app behind the same single flag — a side mock server is what `block-mock-server.py` refuses. Reuse the same handlers in Vitest and Playwright: one handler set, three consumers.

Then STOP and show the user the walkable app. Only after that does real backend work begin.

## Step 5: Verify, then report

Before claiming done, you MUST produce all of the following in the conversation:

- **Diff stat:** `git diff --stat <starting-ref-from-step-1>..HEAD` — show the actual files changed and line counts.
- **Old UI is gone:** `git ls-files | grep -E '<old-ui-paths-from-step-1>'` — must return empty. The old UI is no longer in the working tree.
- **Inventory check:** for every page, route, and component from Step 1's "definition of done", mark each as: ✅ built, ⚠️ stubbed (placeholder/TODO), or ❌ missing. Show the full list.
- **Running evidence:** either a live URL to the new UI running with real data, or a screenshot showing the same. Not the mock — the real wired-up version.
- **Old-vs-new comparison (anti-re-skin proof):** a screenshot of the OLD UI (check out the pre-overhaul rollback ref in a scratch worktree to capture it) next to the NEW one. If they read as cousins — same layout bones, same palette, same structure — it's a re-skin, not an overhaul: say so and redo. "Wow" must be visible here, not asserted.

If ANY of these four cannot be produced, the overhaul is NOT complete. The words "done", "complete", "finished", "shipped", or "overhaul successful" are banned from your response. The correct phrasing is: "incomplete, here's what's left:" followed by the gaps.

If the user asks "is it done?" before this verification is shown, the answer is "no, verifying now" — not "yes" or "mostly" or "essentially".

This step exists because past sessions have claimed completion without delivery. Never again.
