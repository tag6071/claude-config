---
name: rr-ify
description: Convert a manual step into a proper `rr` task (pyproject-runner) following house conventions — <family>-<verb> naming, one-line task with a trailing hash help comment, script under the owning service's scripts/, dry-run default with --apply for mutations, idempotent, docs updated in the same commit. Trigger phrases include "make this an rr command", "rr-ify this", "wrap this in a command", "can't this be a command I run", "make this repeatable", "I thought you already know how we do things" (about commands). Do NOT use for one-offs or alias-sized commands (signal test below refuses premature tooling), or for ~/bin shell scripts (that's playbook/scripts.md territory, not rr).
---

# /rr-ify — manual step → house-convention `rr` task

Any recurring manual step in an rr-managed repo (e.g. an infra repo) becomes a
named, idempotent, documented task. "You know how we roll" — this is how.

## Step 0 — The signal test (refuse premature tooling)

At the SECOND occurrence, rr-ify only if ≥1 fires (same rule as
`playbook/scripts.md` + `/sharpen`):

1. **Cost** — takes >5 minutes by hand?
2. **Mistake-prone** — got it wrong, or reasonably could?
3. **Multi-step / order-matters** — a checklist, not a one-liner?

All three no → say so, don't build. Also: if you can't give it a clear
`<family>-<verb>` name, the abstraction is wrong — stop.

## Conventions (verified against a real pyproject.toml)

- Tasks live in `pyproject.toml` `[tool.pyproject-runner.tasks]`.
- **Name**: `<family>-<verb>` (`backup-run`, `cert-rotate`, `drive-eject`).
  Reuse existing family prefixes; reuse the house verb set (list/status,
  ingest, setup, install/uninstall, diff/apply, rotate, mint).
- **Definition**: one line, `uv run python <service>/scripts/<name>.py` (or the
  shell script), trailing `# comment` = the help text `rr` shows.
- **Script location**: under the OWNING service's `scripts/` dir (e.g.
  `<service>/scripts/`), never a stray top-level file.
- **Safety**: mutating tasks default to dry-run and require `--apply`;
  destructive ones also confirm. Non-mutating status tasks run plain.
- **Idempotent**: running twice = running once. Second run must prove it
  (no duplicates, no re-work).
- **Env**: uv-managed; stdlib-first (build-vs-adopt rule applies to deps).

## The ritual

1. **Name it** — `<family>-<verb>`; check `rr` task list for prefix collisions
   and the nearest sibling to copy style from.
2. **Write the script** — header docstring with description + usage examples
   (future-you forgets syntax); `--help` works; dry-run default if mutating.
3. **Register** — one line in `[tool.pyproject-runner.tasks]`, alphabetical
   within its family block, trailing `#` help comment.
4. **Verify** — run it twice: once dry, once `--apply` (or twice plain if
   read-only). Second run proves idempotence. Show output.
5. **Document in the SAME commit** — the owning service's README section
   (fold, don't spawn a new doc) + TASKS.md if the repo has one.
6. **Commit** — `feat: add rr <name>` with the WHY (which manual pain it
   kills) in the body.
