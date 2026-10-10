---
triggers:
  - '\b(script|client|wrapper|integration)\b.*\bapi\b'
  - '\bagainst (the|a|an|this|their)\b.*\b(api|endpoint|service)\b'
  - '\b(request|response) (body|payload|schema)\b'
  - '\bapi (endpoint|integration|call)\b'
---
[rule:api-probe-first] Before writing any script against a live API, PROBE the actual running endpoint first (curl/httpie/SDK repl) and read what it requires/returns. Don't model request bodies off docs, a similar-looking service, another version, or recollection — sibling APIs in the same product family differ field-to-field version-to-version. Untested API scripts cause fix-round churn that erodes trust.
