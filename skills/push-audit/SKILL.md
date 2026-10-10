---
name: push-audit
description: Pre-remote-push repo audit — secrets (working tree AND full history), junk/large files, LFS candidates, personal info, .gitignore gaps — ending in a GOOD-TO-PUSH / FIX-FIRST verdict table. ANSWER-ONLY — this skill NEVER pushes; pushing is the user's business, always. Trigger phrases include "is it good to push", "safe to push to remote", "should I push this repo", "good to go to push it to remote", "publish this repo", "push to my private repo?". Do NOT use for routine commits to an already-published repo (only the new diff matters there), and never treat the question as authorization to push or to fix anything — report first, act only on an explicit follow-up instruction.
---

# /push-audit — is this repo safe to publish?

Answers ONE question with evidence: "if this repo lands on a remote, what
leaks or embarrasses?" The question "should I push?" is a question — the
deliverable is the verdict table, zero actions.

## Hard rules

- **NEVER run `git push`.** Not even to a private remote. Not after a clean
  verdict. "Pushing is none of your business."
- **Read-only**: no fixes, no history rewrites, no .gitignore edits unless the
  user explicitly asks after seeing the verdict.
- **History counts.** A secret deleted in HEAD but alive in an old commit still
  ships. Every check runs against full history, not just the working tree.

## Checks (run all, in order)

### 1 — Secrets, working tree + full history

```bash
# Preferred: gitleaks if installed (scans history by default)
gitleaks detect --source . --no-banner 2>/dev/null || {
# Fallback: pattern grep over every blob ever committed
git grep -Ei '(api[_-]?key|secret|token|passwd|password|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-)' $(git rev-list --all) -- . 2>/dev/null | head -40; }
# Env/credential files anywhere in history
git log --all --diff-filter=A --name-only --pretty=format: | sort -u | grep -Ei '\.(env|pem|p12|key|keystore)$|credentials|secrets\.(ya?ml|json)'
```

### 2 — Junk + oversized objects

```bash
# Top 15 largest blobs in history
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob"' | sort -k3 -n -r | head -15
# Junk that should never be tracked
git ls-files | grep -Ei '\.DS_Store|node_modules/|__pycache__|\.pyc$|dist/|build/|\.log$|\.sqlite3?$|\.db$'
```

Flag: blobs >5MB → LFS candidates; >50MB → GitHub hard-limit risk.

### 3 — Personal info + identity

```bash
git log --all --format='%an %ae' | sort -u          # unexpected emails/names?
git grep -Ei '/(Users|home)/[a-z]+' -- ':!*.lock' | head -20   # absolute home paths
```

Personal absolute paths are a smell, not a blocker — flag, don't fail.

### 4 — .gitignore gaps + untracked strays

```bash
git status --short              # uncommitted work that would NOT ship — note it
git check-ignore -v .env 2>/dev/null || echo ".env not ignored"
```

### 5 — Repo hygiene

Branch state (`git log --oneline -3`), dangling remotes already configured
(`git remote -v`), submodules pointing at private URLs.

## Verdict table (always the final output)

| Check | Result | Evidence | Fix (command, not applied) |
|---|---|---|---|
| Secrets (tree+history) | ✅ / ❌ | … | e.g. `git filter-repo --path X --invert-paths` |
| Large/junk files | … | … | … |
| Personal info | … | … | … |
| .gitignore | … | … | … |

**Verdict: GOOD TO PUSH** (all ✅) or **FIX FIRST** (any ❌, fixes listed).
History-rewrite fixes (`filter-repo`) get a one-clause warning: rewrites all
hashes — coordinate before running.
