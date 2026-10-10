---
name: worktree
description: Spin up or tear down an isolated git worktree so a parallel Claude Code session never collides with this one. Two sessions in the same checkout fight over .claude/PLAN.md, .claude/3Q.md, and the shared git index — a worktree gives each its own working dir while sharing one .git. git-crypt aware. Trigger phrases include "/wt", "new worktree", "spin up a worktree", "parallel session", "isolated session", "I want to work on X in parallel", "another claude session on this repo".
---

# worktree — parallel Claude sessions without collisions

The engine is `~/.claude/bin/wt` (global, on PATH, any repo, any machine). It handles the
git-crypt key dance that a plain `git worktree add` botches.

## When the user wants a parallel/isolated session

1. **Best path — the user drives it from a pane they open.** Tell them: open a new iTerm
   pane/tab (⌘D / ⌘T) and type:

   ```
   wt <name>
   ```

   The `wt()` shell function (source `~/.claude/bin/wt.zsh` from `~/.zshrc`) drops THAT pane into an isolated worktree and
   starts claude — no paste, no extra pane. No name → next free slot (`<repo>-2`, `-3`, …);
   `wt feature` → named. To spawn a *new* pane instead of taking over the current one,
   append `--vsplit` (⌘D) / `--tab` (⌘T) / `--hsplit` (⌘⇧D) / `--window`.

2. **If you (Claude) run it yourself**, use the print form — you must NOT spawn windows:

   ```
   wt -p <name>
   ```

   It creates the worktree, copies `cd … && claude` to the clipboard, and prints it.
   Relay that line; the user pastes it into a new tab.

## Lifecycle

- **List:** `wt ls`
- **Land it back** (from the hub / main session): `wt merge <name>` — merges `wt/<name>`
  into the current branch, then removes the worktree + branch. Refuses on a dirty tree.
- **Discard:** `wt rm <name>` (add `-f` to force past a dirty/unmerged worktree).
- **Cleanup after a manual folder delete:** `wt prune` — drops stale registrations +
  orphaned `wt/*` branches (merged ones deleted, unmerged kept + reported).

## Rules

- The **main checkout is the hub** — it stays on `main` and is where branches merge back.
  Never open a second `claude` in the hub folder; that's the collision this skill avoids.
- A **running** session can't be relocated into a worktree (its cwd is fixed at launch).
  Worktrees are for NEW parallel work, not migrating an already-open session.
- Each worktree is its own branch `wt/<name>`; a branch checks out in one worktree only.
- git-crypt repos: `wt` links the shared key automatically and verifies the tree is
  clean (decryption succeeded) before declaring success. A plain `git worktree add` does NOT.

## Don't reach for this when

- The user wants many parallel jobs *done* but is happy steering ONE chat → use background
  subagents/tasks instead (no extra windows or branches to juggle). Worktrees are for
  genuinely independent interactive sessions the user drives themselves (~2–3, not 20).
