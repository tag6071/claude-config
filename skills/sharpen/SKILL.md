---
name: sharpen
description: The single overarching introspection + lock-in skill. Invoke `/sharpen` mid-session to reflect on recent exchanges, identify loops / drift / repeated failures / friction, classify findings, propose fixes, and lock them in — routing each fix to the right home (hook / lessons file / CLAUDE.md) at the right scope without bloating always-loaded context. Also the fast path for locking in a single rule: `/sharpen <rule text>`. Subsumes the former `/ingrain` skill. Trigger phrases include "/sharpen", "sharpen this", "let's sharpen", "stop and think about what we just did", "ingrain this", "lock this in", "remember going forward", "from now on always/never X". The full reflection flow is INTERACTIVE-ONLY (Gates 1-4 use `AskUserQuestion`); the fast-path lock-in does not need it. Do NOT auto-invoke the reflection flow — it is a human-pulled reflex.
---

# Sharpen

The single user-pulled reflex for sharpening how we work. It stops the current
trajectory, looks back with fresh eyes, classifies what it finds, proposes
fixes, and **locks them in** — engraving rules, capturing workflows, or
resetting. It is also the one path for locking in a single stated rule.

This skill exists because the in-session Claude is biased: it's invested in the
current path and will rationalize bad approaches. Sharpen breaks the bias with a
fresh-eyes subagent at Gate 2 — full transcript fidelity from main Claude +
independent perspective from the subagent.

It subsumes the former `/ingrain` skill: its **lock-in engine** (below) is how
any rule/lesson gets engraved, whether surfaced by reflection or stated directly.

## Invocation modes

- **`/sharpen`** (no args) — full reflection. Run the 5 gates in order.
- **`/sharpen <rule text>`** — fast lock-in. Skip Gates 1-4, go straight to the
  **Lock-in engine** with the given rule. This is the old `/ingrain <rule>`.

**Early exit is always allowed.** CONTINUE (Gate 4), "nothing worth acting on,"
or the autonomy abort (Gate 1) all bail cleanly. Don't manufacture a finding to
justify finishing the flow — finishing early is a valid, common outcome.

## When to invoke (reflection flow)

- User explicitly asks: `/sharpen`, "let's sharpen", "stop and think".
- User signals friction without the word: "this isn't working", "we keep going in circles", "I think we're stuck".

When NOT to invoke:

- Healthy work in flight, user is satisfied with progress.
- User asked a specific question — answer it, don't sharpen at them.
- Mid-tool-call — wait until the current operation completes.

## The 5 gates

Run strictly in order. Do not skip. Do not collapse. Each gate has a single owner.

### Gate 1 — Pause & state (main Claude, 2–3 sentences)

**Fast-path branch first.** If invoked as `/sharpen <rule text>`, skip to the
**Lock-in engine** — no reflection gates.

**Autonomy check.** If `AskUserQuestion` is unavailable (autonomous / headless,
`--dangerously-skip-permissions` with no human), the reflection flow can't
complete (Gates 3-4 need it). STOP and print:

> `sharpen reflection requires interactive mode. Re-invoke interactively, or use \`/sharpen <rule>\` for a direct lock-in.`

Do NOT proceed through the remaining gates. (The fast-path lock-in does NOT hit
this wall — it has no `AskUserQuestion` dependency.)

If interactive, continue. Stop everything. Write ONE short paragraph:

- What was I attempting in the last stretch?
- Where am I now (committed? dirty? mid-debug?)?
- What was the immediate next step I was about to take?

No spin, no justification. State the facts as a third party would. If you wrote 200 words, you're spinning — cut to 50.

### Gate 2 — Fresh-eyes scan (subagent)

Spawn a `general-purpose` subagent with this brief:

> You are a fresh reviewer with no investment in the current conversation's path. Below are the recent user/assistant exchanges (the last ~5–15, or since the last commit, whichever is smaller) in verbatim form. Read them and identify, in under 200 words:
>
> 1. **Loops** — was the same approach attempted multiple times with the same result?
> 2. **Drift** — did the working goal change between start and now? If yes, by how much?
> 3. **Assumption stacking** — were unverified assumptions layered on each other?
> 4. **Strike count** — count distinct attempts at the SAME underlying problem. If ≥3, flag it.
> 5. **Friction the user repeated** — did the user have to correct or re-ask the same thing?
> 6. **Lock-in candidates** — a repeated workflow (→ skill), a recurring rule/correction (→ rule), or a process gap (→ hook)? Apply the signals: cost (>5 min?), mistake-prone, multi-step.
>
> Be blunt. Don't soften. The user asked for this review.

Pass the verbatim exchanges (don't summarize first — that defeats fresh eyes). The report comes back to main.

### Gate 3 — Diagnose (main Claude + user)

Read the subagent's report. State in ONE sentence: "The actual problem is _____."

- Agree with the subagent? Say so. Disagree? Name it specifically.

Surface the diagnosis to the user as one sentence and ASK: "Does this match what you're feeling?" Wait for confirm/redirect. Don't infer agreement from silence.

### Gate 4 — Decide (main + user, structured choice)

Pick ONE outcome. No "kind of all three." Use `AskUserQuestion` with these options:

- **SHARPEN** — lock in a fix. The fix is one of three shapes (decided at Gate 5):
  a **rule/lesson** (→ Lock-in engine), a **workflow** (→ new skill), or a
  **process gap** (→ a hook). Use ONLY if a signal fires (cost / mistake-prone /
  multi-step) — count alone is not the signal.
- **RESET** — back up to a known-good state. Triggers: path unrecoverable, severe
  drift, or 3+ strikes. State the commit hash. The `RESET` trigger-word semantics
  apply (state last commit, ask before `git reset --hard`).
- **CONTINUE** — explicit "no action, proceed." Triggers when the work is healthy
  and introspection just confirmed it. Don't invent a sharpening to fill the gate.

### Gate 5 — Execute (main Claude)

Execute the Gate 4 decision now. No more discussion.

**SHARPEN path — pick the output shape, then act:**

- **Rule / lesson / constraint** ("never X", "always Y", a recurring correction)
  → run the **Lock-in engine** below. Do NOT write a SKILL.md for a one-line rule.
- **Workflow / process** (multi-step recipe, decision tree, ritual) → write a
  SKILL.md (see *Skill placement* below). Smallest viable skill; refine later.
- **Process gap a hook can enforce** (block an action, check state before a tool
  runs) → write/extend a hook in `~/.claude/hooks/` (or `<repo>/.claude/hooks/`).

**RESET path:** confirm the target commit explicitly → run the reset → ask the
user to restate the goal and verifier in one sentence each (context is stale).

**CONTINUE path:** state "no action — resuming" → resume the pre-sharpen task.

## Lock-in engine (rules / lessons) — folded from ingrain

How any rule/lesson gets engraved. Used by Gate 5 (SHARPEN→rule) and by the
fast path `/sharpen <rule>`. **No `AskUserQuestion` dependency** — runs in
autonomous mode. In autonomous / headless mode (e.g. homeserver,
`--dangerously-skip-permissions`): do NOT wait for interactive approval —
state the rule + the WHY in your response, self-approve per the (optional) plan-gate
autonomous protocol (write `<root>/.claude/PLAN.md`, then `touch PLAN.approved`
yourself), write, and commit. Only the reflection gates (1-4) require
interactivity; this engine is autonomous-safe.

### A. Crisp the rule
Take the rule text (the `/sharpen <rule>` arg, or the finding from Gate 4). If
vague, infer a crisp, imperative one-liner from context.

### B. Pick the TIER — which mechanism (most rules are NOT a CLAUDE.md bullet)
CLAUDE.md loads every message; every line pays rent. Classify:
1. **Enforceable by a hook?** (deterministically blocks an action / checks state
   before a tool runs) → write/extend a hook; leave at most a one-line pointer in
   CLAUDE.md. Then go to E.
2. **Keyword-triggerable?** (fires on a topic detectable in the user's message — a
   tool, file type, task type, command) → drop a lesson file
   `~/.claude/lessons/<slug>.md` with `triggers:` frontmatter (case-insensitive
   regexes). `rule-cards.py` injects it on demand, zero always-on cost. **Do NOT
   append to CLAUDE.md.** Then go to D.
3. **Proactive judgment, no reliable trigger?** (tone, defaults, communication
   patterns the user never names ahead of time) → terse rule + banned-phrases /
   pre-flight in CLAUDE.md. The ONLY tier that earns always-on space. Continue to C.

### C. Pick the SCOPE — global vs project-local (default: PROJECT-LOCAL)
Global pollution is worse than a missing rule. Heuristic:
- **GLOBAL** (`~/.claude/…`) — truly universal: workflow/communication/safety
  patterns that survive a wholesale stack change.
- **PROJECT-LOCAL** (`<repo>/.claude/…` or `<repo>/CLAUDE.md`) — mentions/implies a
  specific language, tool, service, hostname, endpoint, file path, or repo convention.

**Universal-because-X guard (BLOCKING before any GLOBAL write):** state one
sentence — *"This rule is universal because <X>."* If you can't write <X> without
citing a specific tool/service/path/host/language, it is NOT universal — downgrade
to project-local, or generalize the rule text and strip the cite.
- PASSES: "Negative-test probes before trusting output — applies to any protocol on any stack." → global.
- FAILS: "ServiceX v1 endpoint needs field Y" → project-local (or rewrite as "probe API live before scripting against it").

If genuinely unclear after the heuristic, ask ONE specific question.

### D. Write to the chosen home
- **Hook** → the `.py`/`.sh` in `hooks/`, wired into `settings.json`.
- **Lesson** → `~/.claude/lessons/<slug>.md` (global) or `<repo>/.claude/lessons/<slug>.md`, with `triggers:` frontmatter + terse body.
- **CLAUDE.md bullet** (tier 3 only) → append under the closest existing section
  (global) or `## Project rules — locked in` (project-local; create if missing).
  Format: `- [YYYY-MM-DD] <imperative rule text>`. Append only; don't reorder.
  If a project has no CLAUDE.md, run `/claudify` first or create a minimal one.
- **Budget check before any global CLAUDE.md write:** `wc -m ~/.claude/CLAUDE.md`
  must stay well under 40k. If near, condense or push narrative to the lesson/memory
  file — never inflate the always-loaded file.

### E. Memory entry
Write a feedback memory file in the current project's memory dir:
`<project_memory_dir>/feedback_<slug>.md` — standard frontmatter, body = the rule
+ **Why:** + **How to apply:** lines. Add a one-line pointer in `MEMORY.md`.
(For a pure hook with no behavioral nuance, a memory entry is optional.)

### F. Commit
Stage whatever the tier produced (CLAUDE.md bullet / `lessons/` file / hook) plus
the memory file. Global:
```bash
git -C ~/.claude add CLAUDE.md lessons/ hooks/   # only the paths you touched
git -C ~/.claude commit -m "sharpen: lock in <short rule summary>"
```
Project-local: `git -C <repo-root> add … && git -C <repo-root> commit -m "…"`.
If the commit fails on a hook, note it; don't retry destructively.

## Skill placement (Gate 5, SHARPEN→workflow)

- **Global** (`~/.claude/skills/<name>/`) — generic across projects.
- **Repo-local** (`<repo>/.claude/skills/<name>/`) — references repo-specific
  paths, hostnames, subsystems, or commands.
- **Ask** — if you can't tell after 5 seconds. The user knows their portfolio.

## Decision signals (the sharpen rule)

Capture/lock-in ONLY if, at the SECOND occurrence, any of these fire:

1. **Cost** — the manual version takes >5 minutes.
2. **Mistake-prone** — the human got it wrong, or could plausibly.
3. **Multi-step / order-matters** — a checklist, not a one-liner.

If none fire, log it mentally and keep watching. Skill/rule spam is worse than missing one.

## Hard anti-patterns

- ❌ Don't auto-invoke the reflection flow — it's a human-pulled reflex.
- ❌ Don't skip Gate 2. The subagent's independent read is the whole point.
- ❌ Don't collapse Gates 3 and 4. Diagnose first, decide second.
- ❌ Don't sharpen on count alone. Apply the signals.
- ❌ Don't sharpen to look productive. CONTINUE is valid and common.
- ❌ Don't summarize the transcript before the subagent. Verbatim or it's not fresh eyes.
- ❌ Don't default a rule to a CLAUDE.md bullet. Run TIER (step B) — a hook or a `lessons/` file is usually the right home.
- ❌ Don't write a project-specific rule into global without the universal-because-X sentence.
- ❌ Don't write a long artifact "while you're at it." Smallest viable, refine later.

## Final report (after Gate 5)

One line:

```
Sharpened: <SHARPEN|RESET|CONTINUE>. <one-clause result>.
```

Examples:
- `Sharpened: SHARPEN. Rule locked into lessons/diff-before-apply.md (tier 2).`
- `Sharpened: SHARPEN. New skill at ~/.claude/skills/foo/SKILL.md.`
- `Sharpened: RESET. Reset to a033851; awaiting restated goal.`
- `Sharpened: CONTINUE. No action — resuming previous task.`

Nothing more. The artifacts are the evidence.
