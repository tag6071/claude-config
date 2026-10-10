#!/usr/bin/python3
"""
PreToolUse:Bash guard — block spinning a SEPARATE server to preview UI mocks.

Mocks belong IN the app behind ONE flag (e.g. VITE_MOCKS=1), served by the app's
OWN server at the app's OWN single URL (e.g. https://<app>.home.arpa/mocks). A
standalone static server on a side port is the recurring anti-pattern this
blocks — it breaks single-entry / locked-down boxes (homeserver exposes only :443 via
the edge) and muddies the URL story. The user has said "same server, feature
flag, one URL" many times; this guard makes it mechanical, not advisory.

NOT a ban on mock BACKENDS. A mock backend is wanted and expected (the picked UI
direction gets one before the real backend exists) — it just has to live INSIDE
the app. MSW is the sanctioned tool precisely because it does: it intercepts at
the Service Worker layer, same app, same flag, same URL, no process. This hook
refuses the alternatives (json-server / Prism / WireMock / a static `serve`)
because they are all a SECOND SERVER. Full rules: the `mock-backend` rule-card.

Reads JSON from stdin (Claude Code hook protocol). Exit 0 allow / 2 block
(stderr shown to Claude). Bypass: CLAUDE_ALLOW_MOCK_SERVER=1.
"""
from __future__ import annotations

import json
import os
import re
import sys

BYPASS = "CLAUDE_ALLOW_MOCK_SERVER"

# Static / preview server invocations — only at a COMMAND position (start of the
# command or after a shell separator), so a server name quoted inside a commit
# message / echo / grep arg does NOT count as starting a server.
SERVER_RE = re.compile(
    r"(?:^|[\n;|]|&&|\|\||\bcd\s+\S+\s*&&)\s*"
    r"(python3?\s+-m\s+http\.server|http-server|live-server|"
    r"npx\s+serve|serve|vite\s+preview|vite|php\s+-S|busybox\s+httpd)\b",
    re.I,
)
# Historical mock port range 51990-51999 — a dead giveaway of a side server.
MOCK_PORT_RE = re.compile(r"(?<!\d)5199\d(?!\d)")
# A mocks directory being served. `mocks-ui` (the convention) OR a real `mocks/`
# path boundary — NOT the skill name "ui-mocks/" (preceded by '-').
MOCK_PATH_RE = re.compile(r"mocks-ui|(?:^|[\s\"'./])mocks/", re.I)


def main() -> int:
    if os.environ.get(BYPASS):
        return 0
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    server = bool(SERVER_RE.search(cmd))
    target = bool(MOCK_PORT_RE.search(cmd)) or bool(MOCK_PATH_RE.search(cmd))

    # Block only when an actual server tool targets a mocks dir or the mock port
    # range — so unrelated commands that merely mention "mocks" or a 5199x number
    # (commits, greps, docs) are NOT blocked.
    if server and target:
        sys.stderr.write(
            "BLOCKED: this starts a SEPARATE server to preview UI mocks.\n"
            "Mocks must live IN the app behind ONE flag (e.g. VITE_MOCKS=1) and be\n"
            "served by the app's OWN server at its OWN single URL\n"
            "(e.g. https://<app>.home.arpa/mocks) — never a side server, side port,\n"
            "or new DNS name. On locked-down boxes (homeserver = :443 edge only) a side\n"
            "port is unreachable anyway. See the ui-mocks / ui-overhaul skills.\n"
            f"  offending: {cmd[:200]}\n"
            f"  override (rarely right): {BYPASS}=1\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
