---
triggers:
  - '\bls\b.*\|'
  - '\b(script|pipeline|loop|batch|for ?loop)\b.*\b(file|files|rename|mv|cp|concat|enumerate|glob)\b'
  - '\bffmpeg\b.*\bconcat\b'
  - '\b(rename|move|copy) (all|every|the|these)\b.*\bfiles?\b'
---
[rule:ls-aliasing] NEVER use `ls` in scripts/pipelines — it's commonly aliased (eza/exa/lsd/gls) or runs --color, decorating output with quotes/ANSI/icons that corrupt downstream mv/cp/sed/concat lists. Use `find -print0 | sort -z | while IFS= read -r -d '' f`, shell globs when safe, or `/bin/ls` (absolute). Verify with `type ls` BEFORE any file-enumeration pipeline; if aliased, switch immediately.
