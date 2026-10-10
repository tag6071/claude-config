---
triggers:
  - 'i (don.?t|can.?t|do not|cannot) see'
  - 'still (the same|not|shows|see)'
  - 'no such (feature|button|option)'
  - 'nothing (has )?changed'
  - '\brestart(ed)? the (project|server|app)\b'
  - 'forget to restart'
---
[rule:restart-before-verify] Before claiming a change is visible or fixed: restart/reload the serving process YOURSELF and re-verify against the fresh instance ("why do you always forget to restart the project" is a repeat incident). Checklist: (1) is the running process serving the NEW code (restart the server, confirm HMR actually applied, rebuild if compiled)? (2) is the client fresh (hard reload / cache-bust)? (3) re-exercise the exact flow and show evidence. If the user reports "I don't see it / nothing changed", stale process is hypothesis #1 — check it before touching the code again.
