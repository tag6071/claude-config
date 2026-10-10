---
triggers:
  - 'fix (them |it )?all'
  - '\bdo all\b'
  - 'all of them'
  - 'full sweep'
  - 'go all in'
  - 'nothing (must )?remain'
  - 'no cheating'
  - 'do not stop'
  - 'game (the|my) tests?'
---
[rule:completeness-binary] Completeness is binary — 0% or 100%, no middle ground. Protocol: (1) FIRST enumerate the complete target list with an explicit count ("N items found") — that count is the completion contract; (2) work the list; (3) END by verifying count-done == count-enumerated, shown in the report. Partial = not done; "most of them" = failed. NEVER game the verifier: no weakening tests/lint rules to pass, no skipping "hard" items silently, no downgrading scope as an escape hatch. An item that genuinely can't be done is a named ❌ row with the reason — visible, not vanished.
