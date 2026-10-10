---
name: dev-server
description: Use when starting a dev server, web server, watcher, or any long-running development process. Picks the right native watcher per language so edits auto-rebuild/restart without manual intervention. Trigger phrases include "run the app", "start the dev server", "serve it", "preview it locally", "spin up the api", "start the backend", "run it so I can see". Also trigger any time you'd be tempted to tell the user "manually run X after every edit" — STOP, use this skill instead. Do NOT use for one-shot script runs or production deploys — those aren't watched dev processes.
---

# Dev server

Long-running development processes (dev server, API, daemon, anything you'd iterate on) MUST auto-restart on edits. Never tell the user "manually re-run after every edit" — that's a workflow failure, not a workflow.

## Banned phrases

For long-running dev processes, these are workflow failures:

- "now run `<build-cmd> && ./binary`"
- "rebuild and rerun after each change"
- "manually restart when you edit"
- "in another terminal, run …" (when the "run" is the actual app, not a watcher)

If tempted to write any of those — STOP, set up a watcher (one-time cost, then forever zero re-run).

## Step 1: Identify what the project has

Read the project for an existing dev workflow before adding anything:

- `package.json` `scripts.dev` / `scripts.start` (vite, next, nuxt, astro, remix, sveltekit, bun --hot, tsx watch, nodemon)
- `Makefile` `dev` / `serve` target
- `Procfile`, `bin/dev`
- Framework-native: `flask --debug`, `django runserver`, `fastapi --reload` / `uvicorn --reload`, `rails server`, `mix phx.server`
- Existing `.air.toml`, `air.toml`, `.cargo-watch.toml`, `nodemon.json`

If found: **use it directly**. These already handle reload/restart (HMR where possible, process-watch otherwise). Wrapping them in anything else is wrong.

## Step 2: If no native dev workflow, install the right watcher

Pick by language. Always commit the watcher config so the workflow survives across sessions.

| Stack | Watcher | Install | Config |
|---|---|---|---|
| Go | `air` | `go install github.com/air-verse/air@latest` | `.air.toml` (`air init` then customize) |
| Rust | `cargo-watch` | `cargo install cargo-watch` | flag-driven |
| Python (non-framework) | `watchmedo` | `pip install --user watchdog` | flag-driven |
| Elixir | `mix phx.server` (Phoenix) | bundled | none |
| Web (no framework) | `bun --hot run server.ts` | `bun` | none |
| Anything (universal fallback) | `entr` | distro pkg | shell pipeline |

For the universal `entr` fallback:
```
find . -name '*.<ext>' | entr -r sh -c '<rebuild> && <run>'
```
`-r` restarts the child on file change. Pair with the project's real build + run.

## Step 3: Bind to 0.0.0.0 for LAN access

For HTTP servers reachable from the LAN (see `~/.claude/lessons/lan-urls.md`), the listen address must be `0.0.0.0`, not the default `127.0.0.1`. The watcher invokes your run command — bake the host flag into that command:

- Go (via air): `air -- -addr 0.0.0.0:<port>` (args after `--` pass to the built binary)
- Flask: `flask --app app run --host 0.0.0.0 --port <port> --debug`
- FastAPI: `uvicorn app:app --host 0.0.0.0 --port <port> --reload`
- Django: `python manage.py runserver 0.0.0.0:<port>`
- Rails: `bin/rails server -b 0.0.0.0 -p <port>`
- Vite: `vite --host 0.0.0.0`
- Next.js: `next dev --hostname 0.0.0.0`
- Bun: bind `"0.0.0.0"` in `Bun.serve({ hostname: "0.0.0.0", port })`

## Step 4: Last-resort fallback — `claude-app`

`~/.claude/bin/claude-app` exists for the rare case where steps 1–3 genuinely don't fit (multi-process custom orchestration, a weird daemon with no community watcher). It does full kill+respawn (no HMR — strictly worse than language-native tools when one exists).

```
claude-app start "<your-cmd>"
claude-app status
claude-app stop
```

Use ONLY when nothing in step 1–2 applies. Document why in a project NOTE.

## Step 5: Verify, then print the URL

**Verify the server actually responded before printing the URL.** After starting (or after the watcher reports the build succeeded), hit it: `curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:$PORT/` — must return 2xx (or 3xx if the app redirects). If you get nothing / 000 / 5xx, the server didn't come up — port conflict, build failed, crash at startup. **DO NOT print URLs claiming success** — that's a vapor sale. Investigate the watcher's log, fix, retry.

Once verified, print the URL the user clicks. Substitute `$CLAUDE_LAN_HOST` if set (per `~/.claude/lessons/lan-urls.md`) — don't print `localhost` from a remote autonomous box.
