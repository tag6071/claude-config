---
name: design-sweep
description: Whole-app design-system consistency audit + fix — token-scale violations, spacing rhythm, primitive conformance — with a binary-complete section checklist, dev-server restart, and 375px/1280px verification. Trigger phrases include "design sweep", "spacing spacing spacing", "the UI is inconsistent", "did you follow the design system", "full 100% consistency", "fix the spacing everywhere", "make every section consistent". Do NOT use to migrate a UI onto the stack pixel-identically (/ui-conform), to redesign from scratch (/ui-overhaul), or for a single-component tweak (normal UI work) — this is the audit-everything-and-fix pass within the EXISTING design language.
---

# /design-sweep — 100% consistency, verified section by section

The "did you follow the design system?" question, answered before it's asked.
Completeness is binary: every enumerated section gets a verdict — a partial
sweep is a failed sweep.

## Step 1 — Load the law

- The project's token scale: `tailwind.config.*` (named type ramp, spacing
  rhythm, semantic keys). No config-level scale → STOP, that's the actual bug;
  propose the scale first (see [rule:ui-scale] / frontend-design skill).
- The stack primitives: shadcn/Radix components in use (per
  [rule:ui-adopt-dont-reinvent]).

## Step 2 — Mechanical violation sweep (whole repo)

```bash
# Arbitrary values = off-scale by definition
grep -rnE 'text-\[|p[xytblr]?-\[|m[xytblr]?-\[|gap-\[|space-[xy]-\[|leading-\[|tracking-\[' src/
# Bare px / CSS-in-JS escapes
grep -rnE 'font-size:|padding:.*px|margin:.*px|style=\{\{' src/
# Hand-rolled primitives that should be stack components
grep -rnE '<select|role="dialog"|<style>' src/
# Component-owned vertical margins (rhythm must live in gap/space-y on containers)
grep -rnE 'className="[^"]*\bm[bt]-[0-9]' src/ | head -30
```

## Step 3 — Enumerate EVERY screen/section → checklist table

Walk the router/pages dir; list ALL of them with a count ("14 sections found").
This count is the completion contract.

| # | Screen/section | Violations found | Fixed | Verified 375/1280 |
|---|---|---|---|---|

## Step 4 — Fix, one section at a time

- Same role → same token (text-title, gap-section, p-4 …). Replace arbitrary
  values with the nearest NAMED token; if no token fits, that's a scale gap —
  fix the scale once, not the callsite with a `[13px]`.
- Vertical rhythm via `gap`/`space-y` on the stacked container, not per-child
  margins.
- Alignment/placement: match the exemplar section (pick the best one FIRST,
  conform the rest to it).

## Step 5 — Restart, then verify (non-negotiable order)

1. **Restart/reload the dev server** — never judge freshness against a stale
   process ("why do you always forget to restart" is a repeat incident).
2. Screenshot every section at 375px AND 1280px (Playwright), plus all three
   color modes if the app ships them.
3. Re-run the Step 2 greps — must come back empty (or each hit justified).

## Step 6 — Report

The FULL table from Step 3, every row resolved — count fixed == count
enumerated. Lint gate note: if the repo has /install-lint-rails, confirm the
scale checks are wired so this class of drift can't return.
