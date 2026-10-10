---
triggers:
  - 'mock backend|mock api|mock server|fake (backend|api|server)|stub (out )?(the )?api'
  - '\bmsw\b|mock service worker|mswjs'
  - 'walk (through )?the (whole|full|entire) flow|clickable prototype|as if the (whole )?app'
  - 'json-server|mirage ?js|wiremock'
---
MOCK BACKEND — MSW is the sanctioned tool. One handler set, three consumers.

WHEN. NOT for the 3 competing UI mock directions — those stay fake-data-only and
cheap, because two of them get deleted. Build the mock backend for the ONE
direction the user picked: AFTER "go with NN", BEFORE the real backend. That is
the entire point — walk the complete flow, find the design holes while they cost
nothing, and only then commit to the real implementation.

STACK.
- `msw` v2 — intercepts at the NETWORK layer (Service Worker in the browser,
  native in Node). App code makes REAL `fetch` calls: no `if (MOCK)` branch, no
  mock-aware client, nothing to unpick later. REST + GraphQL + WebSocket + SSE
  are all covered — an event/streaming surface is not an excuse to hand-roll.
- `@mswjs/data` — in-memory relational store. CRUD that PERSISTS across the flow,
  so the app behaves as if it were already built. This is what makes the walk real.
- `@faker-js/faker` — only when you need volume beyond a handful of rows.

WHY MSW AND NOT THE OTHERS. json-server / Prism / WireMock / Mirage each spin a
SEPARATE process on a side port — which `block-mock-server.py` refuses, and which
breaks one-app-one-URL. MSW runs INSIDE the app behind the same single flag. It is
the only option already compliant with the house rules. (cf. [[build-vs-adopt]] —
this is question 2: mature OSS covers 100%, so adopt, never hand-roll.)

THE PAYOFF. `src/mocks/handlers.ts` serves the browser mock, Vitest, AND Playwright.
Never write a fixture twice.

CONTRACT-FIRST. Where an OpenAPI spec exists (the Go-backend default), type the
handlers against it (`openapi-msw` / `orval`). The mock then IS the contract the
real backend must satisfy — it stops being throwaway and becomes the spec.

HANDOFF. When the real backend lands, delete the `worker.start()` call. App code
does not change. If you find yourself editing components to "un-mock" them, the
mock was built wrong.
