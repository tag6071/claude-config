# claude-config

My Claude Code setup: global instructions, skills, hooks, an agent, an output style, and a status line.

| Path | What |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Global working rules loaded every session |
| [skills/](skills/) | 18 custom skills (`/sharpen`, `/scaffold`, `/push-audit`, `/nuke`, …) |
| [hooks/](hooks/) | Guards wired in [settings.json](settings.json) (prod isolation, secrets, green-before-commit, terse/persist gates, …) plus their tests |
| [lessons/](lessons/) | Rule cards that [rule-cards.py](hooks/rule-cards.py) injects when a prompt matches |
| [db-explorer.md](agents/db-explorer.md) | Read-only database diagnostic agent |
| [terse.md](output-styles/terse.md) | Terse output style |
| [lint-checks-library/](lint-checks-library/) | Lint checks installed by `/install-lint-rails` |
| [statusline.py](statusline.py) | Status line |

## Install

Everything expects to live at `~/.claude`. Back up yours first, then copy in only what you want:

```bash
cp -R ~/.claude ~/.claude.backup
git clone <this-repo> /tmp/claude-config
cp -R /tmp/claude-config/{skills,hooks,lessons,agents,output-styles,lint-checks-library,playbook,bin} ~/.claude/
cp /tmp/claude-config/statusline.py ~/.claude/
```

[settings.json](settings.json) wires every hook. Merge its `hooks` and `statusLine` blocks into your own `~/.claude/settings.json` rather than overwriting it.

Then edit for your setup:

- [git-identity-allow.txt](hooks/git-identity-allow.txt): replace the placeholders with your git name and email.
- [prod-patterns.txt](prod-patterns.txt) / [secret-patterns.txt](secret-patterns.txt): add your production hosts and secret file names.
- [CLAUDE.md](CLAUDE.md): these are my personal rules. Read it and keep what fits.

Run the hook tests after installing:

```bash
cd ~/.claude/hooks && for t in test_*.py; do python3 "$t" >/dev/null && echo "ok $t" || echo "FAIL $t"; done
```

Some skills and rules assume a home-server setup: apps behind a Caddy edge at `https://<app>.home.arpa`, ops tasks in `rr` (pyproject-runner). Adapt or delete them.

[bin/wt](bin/wt) is the worktree helper the `/worktree` skill uses. Put it on your `PATH`, and add `source ~/.claude/bin/wt.zsh` to `~/.zshrc` so `wt <name>` opens the worktree in the current pane.
