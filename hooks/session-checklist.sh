#!/usr/bin/env bash
# SessionStart hook: inject autonomous-mode working agreements +
# this box's current LAN IP into model context. (Box-agnostic — the
# agreements apply to any repo/host; do not re-brand to a single box.)
#
# LAN IP comes from $CLAUDE_LAN_HOST (set in .zshenv) or autodetect via
# `hostname -I`. We inject as a literal IP so the model doesn't have to
# introspect env vars to know whether to substitute localhost URLs.

lan_ip="${CLAUDE_LAN_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"

url_rule=""
if [ -n "$lan_ip" ] && [ "$lan_ip" != "127.0.0.1" ] && [ "$lan_ip" != "::1" ]; then
  url_rule="\n  URL RULE: this box's LAN IP is ${lan_ip} — every URL you print to the user MUST use http://${lan_ip}:PORT, never localhost / 127.0.0.1 / 0.0.0.0. The user is on another machine; loopback hosts don't reach them. When a tool prints its own localhost URL, reprint with ${lan_ip}."
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "[session-checklist] autonomous working agreements:\n  1. DECIDE & SHIP — pick a sensible default, document the WHY, proceed. Don't wait for input on trivia.\n  2. SMALLEST viable thing first — cabin before cathedral. One change at a time.\n  3. VERIFY before declaring done — green = tests + lint + format + typecheck PASS. You run them. No vapor.\n  4. COMMIT at every green checkpoint — imperative subject + WHY in body. Non-negotiable.\n  5. STEER, don't stall — if a hook blocks you, read its stderr and find another path. Only stop for: an irreversible or prod-touching action without the user's go, intent that is genuinely ambiguous (ask ONE question), or the same problem failed 3x (say RESET recommended).\n  6. END-OF-RUN REPORT when done — shipped (verified), stubbed, broken, TODO, trade-offs, smallest next step.${url_rule}"
  }
}
EOF
