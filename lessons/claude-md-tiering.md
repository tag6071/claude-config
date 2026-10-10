---
triggers:
  - '\bingrain\b'
  - '\bclaude\.?md\b'
  - 'from now on'
  - 'i want you to (always|never)'
  - '\b(add|new) (a )?(standing )?(rule|instruction|lesson)\b'
  - 'remember (that|to|this|always|never|going forward)'
  - 'every (time|session) (you|i)'
  - 'permanent(ly)? (rule|remember|lock)'
---
[rule:claude-md-tiering] Before adding ANY standing instruction to CLAUDE.md, classify it — most rules do NOT belong in the always-loaded file:
  1. Enforceable by a hook? (blocks an action, checks state before a tool runs) -> write/extend a hook in ~/.claude/hooks/; leave at most a one-line pointer in CLAUDE.md.
  2. Keyword-triggerable? (fires on a topic detectable in the user's message) -> drop a ~/.claude/lessons/<name>.md file with `triggers:` frontmatter. rule-cards.py loads it on demand, zero always-on cost. NOT a CLAUDE.md line.
  3. Proactive judgment with no reliable trigger? (tone, defaults, things the user never names) -> terse rule + banned-phrases/pre-flight in CLAUDE.md. This is the ONLY tier that earns always-on space.
Then check the size budget: CLAUDE.md must stay well under 40k chars (`wc -m ~/.claude/CLAUDE.md`). It loads every message — every char is a per-turn tax. Full incident narrative goes to the lessons file or a memory file, never inflates CLAUDE.md. See ~/.claude/lessons/ for the pattern.
