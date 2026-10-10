---
name: user-flow-test
description: Use when building or modifying user-facing functionality (web UI, CLI command, TUI, anything a user interacts with). Ensures user-facing changes have automated test coverage — runs existing tests when they cover the change, writes a new test when they don't, and explicitly skips when the change is trivially safe. Avoids both test bloat (redundant tests for already-covered behavior) and the "go test manually" handoff. Hard rule — the phrases "go verify in your browser", "go test it", "should work now", "give it a try" are BANNED for user-facing work. Mediums covered: web (Playwright via Bun), CLI non-interactive (native subprocess + asserts), CLI interactive (pexpect), TUI (pexpect). Out of scope: desktop GUI, mobile.
---

# User-flow test

Ensure user-facing changes have automated test coverage — by running existing tests when they cover the change, writing a new test when they don't, or explicitly skipping when the change is trivially safe. Avoid both test bloat and the "go test manually" handoff.

## The single rule

> If a human would need to open the app and manually verify this change to be confident it works, an automated test must cover it.
>
> - Existing tests cover it → **run them, show passing output**.
> - Nothing covers it → **write a new test**, run it, commit it.
> - Change is trivially safe (typo, rename, internal refactor with no behavior change) → **no test needed**, but say so out loud.

## Happy-path baseline (required per app)

Every user-facing app MUST have ONE end-to-end test that walks the primary user flow — the hardest realistic thing a real user does — on every commit. It's the safety net that catches incidental regressions in unrelated changes. Without it, every new change becomes a back-and-forth between you and the user: they find the bug, you write a narrow test for that one bug, the next change introduces the next bug, repeat forever.

**Before any narrow per-change test work on a project, check: does the happy-path baseline exist?**

- **No baseline yet** → your FIRST job (before this commit's narrow test) is to create it. Walk every screen, exercise every major input type, click every primary button, traverse the full flow end-to-end. Concretely:
  - **Web app**: empty state → primary user action → full result. Every primary screen visited, every input type filled, every primary button clicked, primary assertions verified throughout.
  - **CLI**: every primary subcommand invoked with valid inputs; assertions on stdout / exit codes / generated files.
  - **TUI**: navigate the main menu, exercise every primary view, exit cleanly.
- **Baseline exists** → run it first. If the current change touches a flow the baseline already covers, extending the baseline is usually right. If the change is genuinely orthogonal, write a parallel flow.

The baseline catches the bug classes a narrow per-change test misses. **If you find yourself writing the third or fourth narrow test on a project that has no happy-path baseline yet, STOP — write the baseline.**

## Why this skill exists

Past failure modes this prevents:

- Building a UI/CLI/TUI feature and telling the user "go verify in your browser" / "should work now".
- Claiming work is done without ever exercising the actual user flow end-to-end.
- Skipping regression coverage so future changes silently break this flow.
- (Opposite failure) Writing a new test for every trivial change — bloating the suite and slowing CI.

## Banned phrases

For user-facing work, these phrases are BANNED:

- "please verify in your browser"
- "go test it" / "try it out"
- "should work now"
- "give it a try"
- "let me know if it doesn't work"

They imply manual verification is needed. If verification IS needed, the right move is to run a test (existing or new), not hand it back to the user.

## Banned reasoning

When scoping a test, these internal reasoning patterns are banned — they produce narrow, reactive tests that let the next bug through:

- *"the user only mentioned X, so I'll test X"* → test the **capability** X belongs to, not just X
- *"I'll add a test for this specific bug"* → what bug **class** does it belong to? test the class
- *"the happy-path test would be nice but the user just wants this one fix"* → if no happy-path exists yet, the user is paying for its absence right now in every back-and-forth — write it first
- *"tests for unrelated areas are scope creep"* → they're not unrelated if the change touches a capability that spans them

## Procedure

### Step 0 — Does this change actually need verification?

Ask: would a competent person feel the need to manually open the app to check this works?

- **If NO** (trivial rename, comment fix, internal refactor with no behavior change, dependency bump that doesn't touch behavior): say `"no test needed because <reason>"` and stop here. Done.
- **If YES**: proceed to Step 1.

### Step 1 — Check existing coverage FIRST

Search for existing tests touching this user flow / component / command. If you find tests that *would have caught a regression in this exact change*:

- Run those tests. Show passing output (including which tests, which file, total time).
- Do NOT write a new redundant test.
- Done — skip the rest of the procedure.

Only proceed past this step if you find a real coverage gap.

### Step 2 — Name the uncovered user flow (BROAD, not narrow)

In plain English, BEFORE writing test code. Not hello-world — the actual end-to-end thing a real user would do (signup → onboard → first meaningful action; pipe stdin through the CLI and check stdout; navigate the TUI to do real work). One sentence in your response.

**Test the CAPABILITY, not the SYMPTOM.** If the change touches a capability (rendering logic, dispatcher, pipeline, parser), the test must exercise the WHOLE capability — every type the dispatcher dispatches, every branch the renderer renders, every input the parser parses — not just the specific case the user mentioned. The user pointed at one bug; the bug class is broader. A test that asserts only what the user complained about will let the next bug in the same class through, and you'll be back here next session writing yet another narrow test.

Example: change is "per-type input primitives in the settings form." **Wrong**: test only the email field the user said was broken. **Right**: test that every catalog DataType renders its correct primitive — money fields locale-formatted, string fields as plain text (NOT money), enum fields as selects with all options, date fields as date pickers — all in one walk.

### Step 3 — Pick the medium's tool

See cookbooks below.

### Step 4 — Set up the test dep if not already present

Into the project's existing toolchain. One-time per project.

### Step 5 — Write the test

At the medium's standard path. Real selectors / real I/O. Real assertions on visible content. NOT blind sleeps and timing-dependent guesses.

### Step 6 — Run the test

Show full output (test name, pass/fail, timing). Don't say "done" while red. **Sanity check**: would this test FAIL on the OLD state? If it passes on both old and new, you tested the wrong thing — redo.

### Step 7 — Commit the test in the same diff as the feature

`feat: <thing> + e2e`. Becomes regression coverage for future changes.

## Verification gate

Before saying "done", "complete", "finished", "should work", or "ready" — you MUST show ONE of:

1. **Passing output from existing tests** that genuinely cover this change, plus a one-liner naming which tests + which behavior, OR
2. **File path + passing output for a new test** written here, plus a one-sentence description of the user flow it covers, OR
3. **Explicit `"no test needed because <reason>"`** — stated openly, not implied.

If you can't produce one of these three, say `"incomplete"` instead. No exceptions.

## Per-medium cookbooks

### Web — Playwright via Bun

Setup:

```bash
bun add -d @playwright/test            # per project — the test runner only
```

**Backend data: reuse the MSW handlers, never re-fixture.** If the app has a mock
backend (`src/mocks/handlers.ts` — see the `mock-backend` rule-card), the test
imports THOSE handlers via `setupServer`, and overrides per-test with
`server.use(...)` for error/empty/latency cases. One handler set, three consumers
(browser mock, Vitest, Playwright). Writing a second, test-only set of fake
responses is a defect — they drift, and the drift is invisible until prod.

**Browser install — once per MACHINE, never per-project, never per-run.** The
default `playwright install` downloads chromium into `~/.cache/ms-playwright`,
which is frequently sandbox/permission-blocked — the recurring failure. Pin a
fixed, writable browsers path so the install happens ONCE in a known place and
every project reuses it:

```bash
# In your shell profile (one time, all projects share it):
export PLAYWRIGHT_BROWSERS_PATH="$HOME/.playwright-browsers"
# Install once into that path (re-running is a fast no-op):
PLAYWRIGHT_BROWSERS_PATH="$HOME/.playwright-browsers" bunx playwright install chromium
```

If the local install is still blocked (locked-down sandbox / CI), use the shared
Docker image instead of installing at all — `mcr.microsoft.com/playwright` ships
the browsers preinstalled; run the suite inside it. ONE shared image for every
app, not a per-app build.

Do NOT run a bare `bun playwright install` into the default cache and hope — that
is the exact thing that fails. (The `stack-conformance` lint pack's
`playwright_browsers_path` check warns when a repo forgets to pin the path.)

Test file (`tests/e2e/<flow>.test.ts`):

```typescript
import { test, expect } from '@playwright/test';

test('user signs up and reaches dashboard', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.getByRole('button', { name: 'Sign up' }).click();
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'Welcome' })).toBeVisible();
});
```

Run: `bun playwright test`

Use role / label selectors (`getByRole`, `getByLabel`) — accessibility-grade, survives cosmetic changes. Avoid CSS selectors unless the role/label option genuinely doesn't exist.

### CLI non-interactive — native subprocess + asserts

No new deps. Use the project's existing test framework (Go `testing`, Python `unittest`, Rust `#[test]`, etc.).

Python example (`tests/test_cli.py`):

```python
import subprocess
import unittest

class TestGreet(unittest.TestCase):
    def test_greets_named_user(self):
        result = subprocess.run(
            ["./bin/greet", "Ada"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("Hello, Ada", result.stdout)
```

Run: `uv run python -m unittest discover tests` (or the project's standard).

### CLI interactive — pexpect

For CLIs with prompts, paging, multi-step interaction.

Setup (once per Python project): `uv add --dev pexpect`

Test (`tests/test_login.py`):

```python
import pexpect

def test_login_flow():
    child = pexpect.spawn("./bin/myapp login", encoding="utf-8", timeout=5)
    child.expect("Username:")
    child.sendline("ada")
    child.expect("Password:")
    child.sendline("secret")
    child.expect("Logged in as ada")
    child.expect(pexpect.EOF)
```

For non-Python projects targeting an interactive CLI, use the project's native subprocess + stdin/stdout dance. pexpect is the cleanest tool when available.

### TUI — pexpect with fixed dimensions

Setup: `uv add --dev pexpect`

Test (`tests/test_tui.py`):

```python
import pexpect

def test_tui_navigation():
    child = pexpect.spawn(
        "./bin/mytui", encoding="utf-8", timeout=5, dimensions=(24, 80),
    )
    child.expect("Main Menu")
    child.send("j")          # navigate down
    child.expect("Settings")
    child.send("q")          # quit
    child.expect(pexpect.EOF)
```

For visual TUI snapshots, capture `child.before` after each interaction and assert on the rendered text.

## Out of scope

- **Desktop GUI** (AppleScript, accessibility APIs, PyAutoGUI) — these fight more than they help. If you must ship a desktop change, write an honest manual checklist for the user and SAY that's what you're doing — do NOT pretend a manual checklist is an automated test.
- **Mobile** — same. Appium exists but adopting it deserves its own conversation.
- **Unit tests** — that's the normal Testing section of CLAUDE.md. This skill is specifically about user-flow tests.
- **Load / perf tests** — different concern entirely.

When the medium is out of scope, the correct phrasing is: `"no automated test path for this medium — here's a manual checklist instead"` followed by the exact steps the user should run. Do not lie about what was tested.
