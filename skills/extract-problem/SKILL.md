---
name: extract-problem
description: Use when the user wants a clean, unbiased restatement of the problem they're trying to solve — typically after a long or stalled session with an LLM, so they can hand the brief to a fresh LLM (or to themselves) without dragging this session's baggage with it. Trigger phrases include "/extract-problem", "extract the problem", "give me a clean problem statement", "what am I actually trying to solve", "I want to hand this to another LLM". Do NOT use during healthy in-flight work where the conversation is still productive — this is for breakout / handoff / reset moments only.
---

# Extract problem

Produce a clean, portable restatement of the user's problem in the user's voice, suitable for handing to a fresh LLM that has zero context on this session.

## The core principle

**Behave like an amnesiac stenographer, not a survivor of a failed brainstorm.**

The single biggest failure mode of this skill is the extracting LLM bleeding its own session bruises into the output and biasing the next LLM. The output must read as if the prior iteration never happened. If a reader can tell from the brief that there was a stalled session before this, the skill failed.

## Procedure

1. **Read the full session, not a summary.** Compaction summaries are biased toward the LLM's framing of what mattered. Go to the raw transcript if available. Pay attention to what the *user* actually said — quotes, requirements, rejections — not what the LLM inferred.

2. **Draft three sections, in the user's voice (first person)**:

   - **The problem** — what the user is trying to solve, why existing options annoy them, what success looks like. Prose, not bullets. Concrete and grounded.
   - **Hard constraints** — the non-negotiables the user stated (tech stack, scope, privacy, budget, environment, language, etc.). Bulleted.
   - **The bar for "done well"** — quality criteria, aesthetic vibes, explicit anti-patterns the user named. Short.

3. **Add an `Open questions` section only if genuinely needed** — for actual unresolved contradictions in what the user said, or load-bearing facts they never specified. Do NOT use it as a dumping ground for LLM uncertainty.

4. **Run the sanity check** (next section) before printing.

5. **Print the brief inline as clean markdown and stop.** No follow-up questions to the user. No offer to refine. No commentary about the extraction itself. The output is the deliverable.

## Strip ruthlessly

Remove from the draft:

- Any meta-commentary about *this* session ("after several rounds…", "iteration stalled because…", "we tried X repeatedly…"). The new LLM should not be able to tell a prior session existed.
- "Lessons learned" from the prior LLM's attempts. Those are the LLM's bruises, not the user's requirements. They bias the next LLM into avoiding things that were actually fine, or into over-cautious behavior.
- Defensive constraints that came from the LLM's failure mode rather than the user's stated principle. Example: "don't generate too many options" is not a real constraint unless the user actually said it as a rule.
- The prior LLM's unaccepted hypotheses. If the LLM proposed Y and the user didn't echo it back, Y is noise — strip it.
- Mockups, code snippets, intermediate artifacts, file paths from in-progress work. Those are session debris, not the problem.
- Apologetic tone, postmortem framing, "we got stuck on…", "to avoid the previous trap…". All forward-looking.
- Names of tools, libraries, or approaches the LLM suggested unless the user adopted them explicitly.

## Don't narrow the problem to the failure surface

If the stalled portion of the session was about one slice (e.g. visual design of a UI), the extracted problem is still the *whole* thing the user is building, not "I need help with the slice that broke." A failed session must not shrink the problem the next LLM sees.

## Sanity check before printing

Re-read the draft as if you have never seen this session. Ask:

- Does this read like a clean problem brief, or like a recovery note?
- Could a fresh LLM read this and form an independent strategy, or would they feel constrained by invisible scar tissue?
- Is anything in here a reaction to *my* failures rather than the *user's* requirement?
- Have I quietly inserted defensive language ("be careful with…", "don't over-…", "make sure to first…")?

If any answer is bad, strip and redraft. Then print.

## What the output looks like

Three sections, markdown headings, first person throughout. Roughly one screen of prose plus tight bullets — long enough to brief a fresh LLM cold, short enough to paste into a new conversation. No preamble before the brief, no commentary after it.

## Hard rules

- No questions to the user during extraction.
- No mention of this session, the prior LLM, or "previous attempts" anywhere in the output.
- No invented requirements. Only what the user actually said.
- No reframing of the user's words into the LLM's preferred vocabulary.
- If the user contradicted themselves mid-session, capture both positions under Open questions — do not pick a winner.
