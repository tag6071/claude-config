---
triggers:
  - '\b(scaffold|bootstrap|init(ialize)?|new)\b.*\b(project|app|repo|service|package|crate|module)\b'
  - '\b(formatter|linter|lint|format)\b'
  - '\b(gofmt|go vet|golangci|cargo fmt|clippy|ruff|biome|prettier|shfmt|shellcheck|eslint)\b'
  - '\b(set up|setup|add)\b.*\b(toolchain|ci|pre-commit|green checkpoint)\b'
---
[rule:toolchain] Every project has a formatter + linter from commit 1, near-default config. The green checkpoint includes BOTH. Prefer the language's bundled tool; else one blessed single-binary tool (no plugin sprawl).
  - Go: gofmt + go vet (bundled floor); **golangci-lint** = the blessed code-quality linter (errcheck/staticcheck/…), required for services, install-once single binary. The lint gate runs it when present; hand-rolled Go checks defer to it.
  - Rust: cargo fmt + clippy
  - Python: ruff format + ruff check
  - JS/TS/CSS/JSON: biome
  - HTML/MD: prettier
  - Shell: shfmt + shellcheck
