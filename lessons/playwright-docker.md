---
triggers:
  - '\b(playwright|puppeteer|screenshot|pixel|e2e|end-to-end)\b'
  - '\b(chromium|headless|browser)\b.*\b(test|shot|capture|render)\b'
---
[rule:playwright-docker] **Screenshots / browser e2e on homeserver run via an EPHEMERAL `docker run --rm mcr.microsoft.com/playwright:<project-version>` — NEVER native chromium.** Native fails on missing OS libs (`libasound.so.2` …); chasing them with an `extra-libs` LD_LIBRARY_PATH shim is a rabbit hole — STOP at the first missing lib and switch to docker. The official image bakes in every lib; version-matched images are pre-pulled. ONE shared image, NOT one container per app — `--rm` ephemerality answers the load concern (start → shoot → exit → zero standing load). Reach a lab app on `127.0.0.1:<port>` with `--network host` (bypasses SSO); mount `-v /tmp/shots:/out`. Verified pattern: `docker run --rm --network host -v /tmp/shots:/out mcr.microsoft.com/playwright:vX.Y.Z-jammy npx -y playwright@X.Y.Z screenshot --full-page <url> /out/x.png`, then scp to Mac + view the PNG.
