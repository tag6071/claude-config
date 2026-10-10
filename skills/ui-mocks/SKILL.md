---
name: ui-mocks
description: Use ONLY when starting UI work from scratch for a NEW project or NEW standalone feature with no existing design direction. Generates 3 fundamentally different mockup directions as standalone routes behind a single mock flag (e.g. VITE_MOCKS=1), served from the SANDBOX env (same app + flag, at <app>-sandbox.home.arpa) — never a separate mock server/port, never on the prod host, prod never displaced. The /mocks viewer is a plain link landing — no iframe, no switcher, no embedding. Do NOT use when modifying, extending, adding features to, or polishing an existing UI that already has design direction — those are normal incremental UI work, not the mocks-first ritual.
---

# UI mocks

Generate 3 fundamentally different working mockups before committing to a single UI direction. Bad UX is the cheapest failure to prevent early.

## Step 0: Confirm scope (mandatory)

Before doing anything, verify this is genuinely a new UI / new standalone feature:

- Check whether `ui/`, `src/`, `app/`, `pages/`, `components/`, `views/`, `screens/`, or framework equivalents already contain UI code with established design direction.
- If yes, **STOP and ask the user** whether to:
  - Match the existing design (skip this skill — do normal incremental UI work), or
  - Genuinely start fresh / overhaul (different procedure — surface that we may need a different approach).
- If unsure, ask. Don't assume.

## Generate

Build 3 directions as **routes in the app behind the mock flag** — `/mocks/01`, `/mocks/02`, `/mocks/03` (gated by `VITE_MOCKS=1` or the stack equivalent). Each is a full working view of the medium. Do NOT create a standalone `mocks-ui/` static site — that's the old separate-server anti-pattern (the `block-mock-server` hook refuses serving it).

**Apply the `frontend-design` skill's process to every direction** — this is where "best-in-class / wow" comes from, and it's not optional. For each direction: ground it in the subject, pick a deliberate design thesis, characterful typography, a signature element, intentional motion. If a direction reads like a generic template you'd produce for any brief, redo it. Generic "modern SaaS" energy across the board is a failure.

Three gates, all required:
- **Gate 1 — thesis before pixels.** Write a one-paragraph design thesis per direction first (the specific, unusual concept; signature element; type intent). "Clean/modern/minimal" is a generic default — reject and rewrite before coding.
- **Gate 2 — independent distinctiveness critic before showing the user.** Run a fresh-eyes critic (subagent, no context of how you built it) on each: *"distinctive intentional design for THIS subject, or a generic template? verdict + reason."* Generic → redo or drop. Self-grading "wow" is a lie; the critic breaks it.
- **The 3 COMPETING mocks are CHEAP and come FIRST.** Hardcoded-fixture views only — no backend, no feature build, no real data layer. A minimal app shell + the 3 mock routes, nothing more. **Never build the whole app before the user picks** — two of these get deleted, so anything beyond pixels is wasted. (The *picked* direction DOES get a mock backend — see [Mock backend](#mock-backend-after-pick-picked-direction-only) below. Don't build it for all three.)

- Each mock is a fundamentally different **direction**, not a variation. If two feel like siblings, redo one immediately — with only 3 slots, every one has to count. The 3 should explore genuinely different shapes — different layouts, different interaction models, different mental metaphors, different information hierarchies. Pick the directions yourself based on what makes sense for the domain.
- Each mock must work end-to-end through a realistic full instance of the app's hardest real task — not a hello-world click. The flow must exercise every primary interaction the real app needs.
- Hardcoded realistic sample data. State changes feel live. Animations, feedback, errors, empty states all designed.
- For visual mediums: render at relevant sizes (mobile + desktop for web; whatever sizes matter for the target). **EVERY mock implements all three color modes** — auto (default, follows `prefers-color-scheme`), light, dark — with an in-mock toggle. Both light and dark must look finished, not afterthoughts. This is non-negotiable.
- Be visually adventurous. Don't default to one aesthetic. The 3 should cover a wide visual range. Generic "modern SaaS dashboard" energy is a failure mode — one of those is fine, all 3 is not.
- Each must look like a finished product, not a wireframe. Real copy, real microcopy, real density, real spacing. Screenshot-credible as the shipping product.
- Walk the hardest user flow in your head. If you can imagine friction at any step — slow, awkward, fiddly, requires re-reading — redo that mock.

## Viewer shell — sidebar is GOOD; the jank is iframes/reloads, NOT the sidebar.

The `/mocks` route is a viewer with a **sidebar**: the 3 directions + a global auto/light/dark toggle + a responsive-width control (375 / 768 / 1280). Clicking a direction renders THAT direction's component **directly in the content pane** — a plain client-side component/route swap in the SAME SPA instance, no reload, no remount of the app. Each sidebar item also carries an **"open full ↗" link** to the standalone route (`/mocks/0N`, new tab) for a true full-viewport view. The width control simply constrains the content pane's width — mocks are mobile-first, so the constrained container previews each breakpoint.

Each `/mocks/0N` is a standalone route rendering the SAME direction component full-screen (the target of the ↗ links).

**The ONE hard ban — THIS, not the sidebar, caused every white flash / double-render / auto-jump / double-select:**
- **NO `<iframe>`** to embed a mock — an iframe reloads the whole app per click (white flash, double-mount).
- **NO full-app reload/remount on switch** — switching directions changes which component renders (React state/route); the app instance never remounts.

A sidebar that swaps a **rendered component** client-side is correct and encouraged. A sidebar that swaps an **`<iframe src>`** (or reloads the page) is the defect. That difference is the entire bug — the directions are plain components, so render them directly.

## View — mocks live in the SANDBOX, behind a flag. NEVER on the prod host, NEVER a separate server.

Mocks are routes in the SAME app gated by ONE flag, served from the **sandbox** environment — not a second server, not a picked port, not a new mock DNS name, and **NEVER on the production host**. Two environments only (see the `lan-urls` rule-card): production stays live at `<app>.home.arpa`; the sandbox runs the same app with the flag on at `<app>-sandbox.home.arpa`. (A side static server on a high port, or displacing prod with a dev container, are the recurring failures — the `block-mock-server` hook refuses the former.)

1. **Mocks are routes behind a single flag.** `VITE_MOCKS=1` (or the stack equivalent) ADDS `/mocks` (the landing) + `/mocks/01`, `/mocks/02`, `/mocks/03`. Flag off → routes aren't in the bundle. Not a standalone `mocks-ui/index.html`.
2. **Prod is never touched.** Showing mocks must NOT take the live app offline or claim `<app>.home.arpa`. The sandbox runs side-by-side on its OWN host.
3. **Serve through what the USER's browser can actually reach** (port-agnostic — homeserver exposes ONLY `:443` via the edge; any raw dev port is firewall-blocked):
   - **Edge-served app (the common case):** run the sandbox HMR container with `caddy: <app>-sandbox.home.arpa` (template `~/.claude/lint-checks-library/templates/compose.dev.yml`, flag on) → mocks at **`https://<app>-sandbox.home.arpa/mocks`**, prod still live at `<app>.home.arpa`.
   - **Plain local box where the dev port is genuinely browser-reachable:** the dev URL + `/mocks` is fine (`$CLAUDE_LAN_HOST` if set, else localhost).
4. **Verify from where the USER is, not `localhost` on the box.** curl the sandbox edge url, expect 200 (or 302→SSO). A `200` on `localhost:5173` from the box proves NOTHING. If it doesn't respond, say so and fix the serving.

## Stop and wait

After serving, STOP. Do not begin backend work or finalize anything. Wait for "go with NN". Then make that direction the app's real UI, delete the other two mock routes AND the `VITE_MOCKS` flag/gate (the chosen direction becomes the default, not a flagged route), and proceed to "Lock in the design system" below.

This is the one place mid-build where you stop for input.

## Lock in the design system (after pick)

After promoting the chosen mock to `ui/`, do these five steps BEFORE any new feature work. This locks the design language so future sessions compose from it instead of inventing — which is the #1 cause of drift after mock-pick.

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

## Mock backend (after pick, picked direction only)

The picked mock is still a puppet: fixtures hardcoded per screen, no state carried between them. Before committing to the real backend, make the ONE chosen direction behave as if the whole app were built — so the user walks the complete flow and finds the design holes while they're still free to fix.

**Never do this for all 3 directions** — two get deleted; it's pure waste. Only after "go with NN".

Adopt **MSW** (`msw` v2 + `@mswjs/data`) — see the `mock-backend` rule-card for the full rationale and the handoff rule. In short: it intercepts at the network layer, so the app makes real `fetch` calls with no mock-aware code, and it runs INSIDE the app behind the same flag (a side mock server is what `block-mock-server.py` refuses).

1. `bun add -D msw @mswjs/data` + `bunx msw init public/ --save`.
2. `src/mocks/db.ts` — `@mswjs/data` factory modelling the app's real entities. This is what makes state persist across the flow.
3. `src/mocks/handlers.ts` — one handler per endpoint the app will really have. Where an OpenAPI spec exists (the Go-backend default), type the handlers against it so **the mock IS the contract** the backend must satisfy.
4. Start the worker behind the SAME single flag (`VITE_MOCKS=1`) in `main.tsx` — never a second flag, never a second server.
5. Reuse the same handlers in Vitest (`setupServer`) and Playwright. One handler set, three consumers — never write a fixture twice.
6. Walk the app's hardest full flow end-to-end as a real user would, with an automated user-flow test (see the `user-flow-test` skill). Latency, errors, empty states and optimistic updates are all mockable — exercise them, don't just cover the happy path.

Then STOP and show the user the walkable app. Design holes surfaced here are the cheapest ones they will ever fix. Only after that does real backend work begin — and when it lands, you delete `worker.start()` and the app code does not change.
