---
triggers:
  - '\b(dev ?server|web ?server|serve|preview|spin up)\b'
  - '\b(bind|host|0\.0\.0\.0|localhost|127\.0\.0\.1|port)\b'
  - '\b(listen|expose)\b.*\b(server|app|service|api)\b'
  - '\b(mock|mockup|sandbox|feature[ -]?flag)\b'
---
[rule:lan-urls] **An app served behind the edge (a `<name>.home.arpa` Caddy route — anything on homeserver) → ALWAYS print `https://<name>.home.arpa`, NEVER an IP, localhost, or ANY raw port.** This is port-agnostic: a locked-down / single-entry box exposes ONLY `:443` (the edge), so EVERY raw port — whatever the number (3000, 5173, 8080, 51990, anything) — is firewall-blocked and dead from the user's browser. The serving port is irrelevant; the only reachable URL is the edge one. Verify the edge URL from off-box (200, or 302→SSO) — a 200 on `localhost:<anyport>` from the box proves nothing. ONLY on a NON-locked-down box where a raw port is genuinely LAN-reachable: if `CLAUDE_LAN_HOST` is set, bind 0.0.0.0 and use that host; unset → localhost.

**Exactly TWO environments: `sandbox` + `production`. There is NO "dev" tier.** Production = the shipped image at `https://<app>.home.arpa`, flag off. Sandbox = where you work (HMR hot-reload) and where mocks are shown, served at its OWN `https://<app>-sandbox.home.arpa` route. The two run SIDE BY SIDE on their own hostnames — **sandbox NEVER claims the prod host, NEVER takes prod down.** Any container serving on `<app>.home.arpa` that is not the shipped prod image is the DEFECT this rule kills.

**Sandbox = HMR through the edge, NOT a raw dev port and NOT a per-change image rebuild.** Run `vite dev` (HMR) in a thin container, SOURCE BIND-MOUNTED, with `caddy: <app>-sandbox.home.arpa` → instant hot-reload at `https://<app>-sandbox.home.arpa`, no rebuilds, prod still live at `<app>.home.arpa`. Template: `~/.claude/lint-checks-library/templates/compose.dev.yml` (set the sandbox host label). `docker compose up -d --build` on the prod compose = SHIP. Requires `server.allowedHosts: ['.home.arpa']` + `hmr.clientPort: 443` in the vite config (else vite rejects the proxied Host). Docker wraps the dev server; it does not rebuild per edit.

**Mocks live behind a feature flag (e.g. `VITE_MOCKS=1` → `/mocks` routes) INSIDE the sandbox app — NEVER a separate mock container, NEVER on the prod host.** Mocks are a sandbox concern: same app, flag on, served at `<app>-sandbox.home.arpa`. Production never carries the mock flag and is never displaced to show mockups.
