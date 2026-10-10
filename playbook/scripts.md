# Script writing conventions

Apply these to every script in ~/bin.

## Shape

- Shebang: `#!/usr/bin/env bash` (or `#!/usr/bin/env python3` etc).
- `set -e` so failures stop the script. Add `set -u` if you handle
  unset vars explicitly.
- Top of file: comment block with description + usage examples
  + 1-line trailer per arg or subcommand.
- `--help` / `-h` flag prints that block:
```bash
  if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
  fi
```
- No-args default: stateful tools (apps, fw) show current state.
  Action tools (snapshot, backup) show help.
- Unknown verb: print "unknown: X" + help, exit 1.

## Verbs

Prefer a small set, reused across scripts:
- `list` / `ls` — show state (default for stateful tools)
- `on` / `off` — toggle
- `stop` — stop one
- `only` — stop everything except one
- `nuke` / `stop-all` — stop everything
- `pin` / `unpin` — name something for shorter typing
- `push` / `pull` — direction-explicit data movement

## Naming

- Short. You're typing it. `fw`, `apps`, not `firewall-toggle`.
- Verbs over nouns when both fit. `snapshot` reads as "make snapshot".
- No prefixes like `my-`, `pc-`, `local-`. Just the name.

## Safety

- Refuse to do destructive things without confirmation OR an explicit
  flag.
- Refuse to upload/zip if obvious secrets are present (see `snapshot`).
- Never `rm -rf $VAR/*` without checking `$VAR` is non-empty.
- Prefer SIGTERM before SIGKILL. Give 0.5s.

## Self-documenting

- Embed examples in the header comment. Future-you forgets the syntax.
- State the WHY in non-obvious decisions as a comment.
- Append to `~/bin/README.md` when adding a new script.

## When to add a script vs not

At the SECOND occurrence of a pattern, evaluate against three signals:

1. **Cost** — did this take >5 minutes?
2. **Mistake-prone** — did you (or could you reasonably) get it wrong?
3. **Multi-step / order-matters** — is it a checklist, not a one-liner?

If any one fires → add the script. If all three say no → keep watching,
no script yet. **Signal beats count** — script spam is worse than
missing one. (Same rule as `/sharpen`'s capture criteria.)

Plus two structural filters that always apply:
- The thing has a clear name (if you can't name it well, the
  abstraction is wrong)
- You'll use it for months, not days

Don't add when:
- It's a one-off
- It's already an alias-sized command (just `alias` it)
- You haven't felt the pain yet — premature tooling is procrastination

## Distribution

`~/bin` should be a git repo. Note machine-specific scripts in the README. Commit when you add or substantively change one.
