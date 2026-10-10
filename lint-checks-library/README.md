# `~/.claude/lint-checks-library/`

Global library of lint-check packs. Installed into projects by the
`/install-lint-rails` skill (`~/.claude/skills/install-lint-rails/SKILL.md`).

## Three-layer scaffolding architecture

| Layer | Skill | Drops in | When to use |
|---|---|---|---|
| Floor | `/claudify` | Skinny `CLAUDE.md`, `.claude/skills/` | Any repo |
| Navigation | `/claudify deep` | `docs/CODE_MAP.md` + `LESSONS.md` + `API-QUIRKS.md` + `scripts/audit-docs.sh` + `scripts/ai-brief.sh` | Mature repos (>10 commits, >2 days) |
| Enforcement | `/install-lint-rails` | `scripts/lint-anti-patterns.sh` + `scripts/lint-checks/` + `Makefile` + wires `scripts/pre-commit` | Mature repos where regressions cost time |

Surfaced automatically by `~/.claude/hooks/repo-maturity-check.sh` on every session start — see "The maturity hook" below.

## Library structure

```
~/.claude/lint-checks-library/
├── _template/                          ← copied INTO each project
│   ├── lint-anti-patterns.sh           (orchestrator template)
│   ├── Makefile
│   └── pre-commit
├── universal/                          ← always applied
│   ├── pack.toml
│   ├── file_growth.sh                  (fail) — >250 lines in one commit
│   ├── section_markers.py              (fail) — multi-line section titles
│   ├── codemap_drift.py                (warn) — needs docs/CODE_MAP.md
│   ├── no_ls_in_pipelines.sh           (fail)
│   └── todo_without_ref.sh             (warn)
├── playwright/                         ← if @playwright/test detected
├── python/                             ← if pyproject.toml or *.py
├── node/                               ← if package.json
├── go/                                 ← if go.mod
├── rust/                               ← if Cargo.toml
└── shell/                              ← if scripts/*.sh
```

Each pack: a `pack.toml` (metadata + check list with severities) + one file per check.

## Adding a new pack

1. `mkdir ~/.claude/lint-checks-library/<name>/`
2. Write `pack.toml`:
   ```toml
   [pack]
   name = "<name>"
   version = "1"
   description = "..."
   applies_when = "<name>"          # or "always" for universal-style
   detect_globs = ["<manifest>"]    # globs that signal this stack
   detect_substring = "<optional>"  # required substring in any matched file

   [[checks]]
   file     = "my_check.sh"
   severity = "fail"                # or "warn"
   needs    = "docs/CODE_MAP.md"    # optional precondition
   ```
3. Add the check file(s). Each:
   - Exits 0 on clean, 1 on hard violation (warn-only checks always exit 0).
   - Prints findings to stdout as `file:line: message`.
   - (Escapes are banned project-wide by no_escape_comments — checks must NOT honor bypass comments.)
   - Bounds its scope (`git ls-files` preferred over recursive walks).
4. Next `/install-lint-rails` invocation in a matching project auto-installs it.

## Adding a check to an existing pack

Drop the file in the pack dir + add a `[[checks]]` entry to its `pack.toml`. Idempotent re-run picks it up.

## The maturity hook

`~/.claude/hooks/repo-maturity-check.sh` runs on every session start. In any git repo with ≥10 commits and ≥2 days of history, it checks for `CLAUDE.md`, `docs/CODE_MAP.md`, and `scripts/lint-anti-patterns.sh`. Missing ones surface as `[maturity]` lines in the session context, pointing at the skill that installs them.

### Disabling — per repo

```bash
touch <repo>/.claude/maturity-check.skip
```

### Disabling — globally

Either remove the hook entry from `~/.claude/settings.json`:

```bash
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path.home() / ".claude" / "settings.json"
d = json.loads(p.read_text())
hooks = d["hooks"]["SessionStart"][0]["hooks"]
d["hooks"]["SessionStart"][0]["hooks"] = [
    h for h in hooks if "repo-maturity-check" not in h.get("command", "")
]
p.write_text(json.dumps(d, indent=2) + "\n")
EOF
```

Or raise the thresholds so no repo qualifies:

```bash
export CLAUDE_MATURITY_MIN_COMMITS=999999   # effectively off
# or in your shell rc for persistence
```

### Tuning the thresholds

Env vars override the defaults (`MIN_COMMITS=10`, `MIN_AGE_DAYS=2`):

```bash
export CLAUDE_MATURITY_MIN_COMMITS=25
export CLAUDE_MATURITY_MIN_AGE_DAYS=7
```

## Relationship to existing global config

- `~/.claude/CLAUDE.md` — standing principles. Text layer.
- `~/.claude/hooks/plan-gate.py` — optional plan-before-edit nudge (not wired by default).
- `~/.claude/hooks/commit-nudger.sh` — nudges commits at green. Pre-existing.
- `~/.claude/hooks/session-context.sh` — injects branch/status/commits. Pre-existing.
- `~/.claude/hooks/repo-maturity-check.sh` — surfaces missing scaffolding. **NEW.**
- `~/.claude/skills/install-lint-rails/` — the orchestrator. **NEW.**
- `~/.claude/lint-checks-library/` — the packs. **NEW.**

The text layer says what the standard is. The hook layer makes it impossible to forget.
