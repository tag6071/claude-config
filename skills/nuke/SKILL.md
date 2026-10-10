---
name: nuke
description: Completely purge an app/tool from this Mac with proof of zero remnants. Enumerate-first ritual — full kill-list table, per-target confirmation, launchctl bootout before deletion, post-delete rescan. Trigger phrases include "nuke X", "remove X completely", "uninstall X fully", "purge X from my mac", "get rid of X entirely", "wipe out all X stuff". Do NOT use for merely disabling/stopping a service (that's a toggle, not a purge), for deleting user data files an app pointed at (source data is NEVER a remnant), or on homeserver/remote boxes (Mac-only ritual; remote purges belong in your infra-as-code repo).
---

# /nuke — total macOS purge with verification

Purges an app/tool and everything it scattered, then PROVES nothing is left.
Exists because "remove X completely" is improvised every time and remnants
(launchd jobs, brew deps, caches) survive ad-hoc deletion.

## Hard rules

- **Enumerate before deleting.** No `rm` until the full kill list is on screen.
- **The kill list needs the user's "go".** One confirmation for the whole table
  (not per file) — but any row marked `?` (ambiguous ownership) needs explicit
  per-row approval.
- **Never delete data the app merely pointed at** — libraries, documents,
  media, repos it indexed. Only the app's OWN artifacts. When unsure, mark `?`.
- **`launchctl bootout` / `osascript quit` BEFORE file removal** — deleting
  files under a running daemon leaves ghosts.
- **Never `rm -rf "$VAR"` without proving `$VAR` is non-empty and expected**
  (playbook/scripts.md safety rule). Echo the resolved path first.
- **Time Machine/backup note**: purge is forward-only; say so in the report.

## The ritual

### Step 1 — Discover every trace

Sweep ALL of these (case-insensitive name + known bundle ids):

```bash
APP="<name>"   # and bundle id(s), e.g. com.vendor.app
# Running state
pgrep -il "$APP"; launchctl list | grep -i "$APP"
# App bundles + CLI binaries
mdfind "kMDItemKind == 'Application'" | grep -i "$APP"; ls /Applications ~/Applications 2>/dev/null | grep -i "$APP"
command -v "$APP"; ls ~/bin /usr/local/bin /opt/homebrew/bin 2>/dev/null | grep -i "$APP"
# Per-user artifacts
for d in "Application Support" Caches Preferences LaunchAgents Logs Containers "Group Containers" "Saved Application State" WebKit HTTPStorages; do
  ls ~/Library/"$d" 2>/dev/null | grep -i "$APP"; done
# System-wide
ls /Library/{Application\ Support,LaunchAgents,LaunchDaemons,Preferences,Logs,PrivilegedHelperTools} 2>/dev/null | grep -i "$APP"
# Package managers + login items + dotfiles + containers
brew list --formula --cask 2>/dev/null | grep -i "$APP"
osascript -e 'tell application "System Events" to get the name of every login item' | grep -i "$APP"
ls -d ~/.*"$APP"* ~/."${APP}"* 2>/dev/null
docker images 2>/dev/null | grep -i "$APP"; docker volume ls 2>/dev/null | grep -i "$APP"
```

Also check: receipts (`pkgutil --pkgs | grep -i`), kernel/system extensions
(`systemextensionsctl list`), Safari/Chrome extensions if app-relevant.

### Step 2 — Kill-list table → user "go"

| # | Path / item | Type | Size | Owner sure? | Action |
|---|---|---|---|---|---|

`Owner sure?` = ✓ (clearly the app's) or `?` (ambiguous — needs per-row OK).
Include the brew uninstall / pkgutil forget / bootout commands as rows.

### Step 3 — Execute in order

1. Quit/kill processes → `launchctl bootout gui/$(id -u)/<label>` each job.
2. `brew uninstall --zap` where brew-owned (zap covers most of ~/Library).
3. Remove login items, then files (per-path `rm -rf`, echoing each).
4. `pkgutil --forget` receipts; docker rmi/volume rm where applicable.

### Step 4 — Prove zero remnants

Re-run the ENTIRE Step 1 sweep. Every probe must come back empty.

### Step 5 — Report

Final table: item → removed/kept(why) → post-scan result. Anything kept
deliberately (user data) is listed, not silently skipped.
