---
name: 3q
description: Force a three-question diagnostic ritual (Q1 Can't it be automated? / Q2 How did we get here? / Q3 How not fall in again?) before proposing any fix or running any state-mutating action. Writes the answers to <project>/.claude/3Q.md so the gate hook accepts subsequent mutations. Trigger phrases include "/3q", "run the three questions", "three-question ritual", "why did this happen", "how do we prevent this" — and invoke it unprompted before any fix to a recurring failure or any state-mutating command the gate hook would question. Do NOT use for pure reads/diagnostics — those are always free.
---

# /3q — The three-question discipline gate

Called before proposing any fix, running any state-mutating
command (`rr apply`, `terraform apply`, destructive git push,
`kubectl apply`, ...), or making any non-trivial code change
in response to a bug or unexpected state.

## When to use

- The user types `/3q`.
- Before I propose any "let's fix it with X" sentence.
- Before running any tool that the
  `~/.claude/hooks/three-questions-gate.py` hook would block.
- ANY time the prompt-impulse is to act on a theory rather than
  on confirmed evidence.

## When NOT to use

- Pure read-only investigation (grep, ls, cat, ping, query).
- Tiny edits already covered by other gates' tiny-edit escape
  valves.
- Routine commits where the underlying change has already been
  audited via three-questions in this session.

## Steps

### 1. Locate the project root

Walk up from the current working directory looking for `.claude/`
or `.git/`. The project root is the closest match. The questions
file lives at `<project-root>/.claude/3Q.md`.

If no project root can be located, default to writing the file at
`./3Q.md` and warn the user.

### 2. State the proposed action / problem in one sentence

What is about to be done? What would the next tool call mutate?
"Let's fix myhost's network config by re-applying the IaC role" is a
proposal. "I need to understand why myhost isn't getting DHCP"
is a problem statement. Both are valid entry points.

### 3. Answer the three questions in writing

Write `<project-root>/.claude/3Q.md` with the following template:

```markdown
# Three-Questions Audit — YYYY-MM-DD HH:MM:SS

## Proposed action / problem

<one-sentence statement>

---

## Q1 — Can't it be automated?

<answer>

- If the proposed action is manual: WHY can't it be IaC?
  Valid reasons:
    • Genuinely one-time, not worth scripting
    • System exposes no programmatic interface
    • Action requires human judgment that can't be encoded

- If the proposed action IS automated already: confirm the
  automation path (file / role / command) and proceed.

- INVALID reasons (= caught laziness):
    • "It's faster to do it manually" (true only the first time)
    • "I'll automate it later" (you won't)
    • "It's just a one-line change" (so was the last one)

## Q2 — How did we get into this problem in the first place?

<answer>

Valid answers:
  a. Specific event / commit / log line / command that caused
     this. (Best — you have evidence.)
  b. Hypothesis with a concrete plan to confirm it. (OK —
     diagnosis is the next step.)
  c. "I don't know." (Honest — and the work is diagnosis,
     not a fix.)

INVALID:
  • "X is probably the cause." (Probably is a guess.)
  • Any "let's try Y" without (a) or (b) above.

## Q3 — How can we not fall into this trap again?

<answer>

Valid answers:
  • A regression test that fails today, passes after the fix.
  • A new hook / assertion / lint rule.
  • A `docs/LESSONS.md` entry with commit-hash provenance.
  • A structural change that makes the bug class impossible.

INVALID:
  • "We'll be more careful next time."
  • "I'll remember to check this."
  • "It only happened once."

---

## Greenlight

[ ] All three answered with real content
[ ] No "I don't know" gaps remain on Q1 or Q3
    (Q2 may be "I don't know" — that means the next step is
     diagnosis, NOT the proposed action)
[ ] Proceeding with: <restate action>
```

### 4. Self-audit before saving

Reread each answer. Specifically:

- Is Q1's answer a real reason this can't be automated, or am I
  rationalizing?
- Does Q2's answer cite specific evidence, or am I guessing?
  If guessing — change Q2 to "I don't know" and reject the
  proposed action.
- Does Q3's answer name a concrete artifact (test, hook, entry,
  structural change), or is it "I'll be careful"?

If any answer fails its self-audit, the proposed action is
**not greenlit**. Revise the proposal or pause for diagnosis.

### 5. Write the file and confirm

After self-audit passes:

```
echo "Three-questions audit recorded at <path>"
echo "Q1: <one-line summary>"
echo "Q2: <one-line summary>"
echo "Q3: <one-line summary>"
echo
echo "Greenlit. Hook will accept state-mutating commands for"
echo "the next 30 minutes (until the file is older than that)."
```

If the proposed action is NOT greenlit:

```
echo "Three-questions audit blocked the proposed action."
echo "Specific gap: <which question failed and why>"
echo
echo "Pivot: <next step — usually diagnosis, not a fix>"
```

### 6. After greenlight

Proceed with the proposed action. The PreToolUse hook
(`~/.claude/hooks/three-questions-gate.py`) will check that the
file exists + is within 30 minutes old and allow state-mutating
commands.

The file at `<project-root>/.claude/3Q.md` persists for the
duration of the work — re-read it before resuming the work next
session, or re-invoke `/3q` for a fresh audit.

## Anti-patterns

- ❌ Writing answers as inner monologue without committing them
  to the file. The act of writing is the discipline. Internal
  answers don't count.
- ❌ Skipping the self-audit step. The whole point is catching
  weak answers before they become weak fixes.
- ❌ Accepting "X is probably the cause" as a valid Q2. Probably
  is a guess. Q2 doesn't accept guesses.
- ❌ Accepting "we'll be more careful" as a valid Q3. Careful is
  not a control.
- ❌ Invoking on read-only investigation (grep, ls, ping).
  Read-only isn't a fix; the discipline is for mutations.

## Companion entries

- Rule card: `~/.claude/lessons/three-questions.md`. The rule is the
  documented contract; this skill is the convenient interface.
- Enforcement hook: `~/.claude/hooks/three-questions-gate.py`.
  Blocks state-mutating bash commands unless `3Q.md` is fresh.
