---
triggers:
  - '\b(fix|patch|repair|workaround|hotfix)\b'
  - '\b(root cause|recurr|keeps happening|again|same (bug|issue|problem))\b'
  - '\b/?3q\b'
---
[rule:three-questions] Before a fix or a state-mutating action, run THE THREE QUESTIONS (advisory ritual, `/3q`): Q1 can't it be automated? Q2 root cause, not guess? Q3 how prevent recurrence? A gap in any answer IS the work. (Also nudged by three-questions-gate.py hook.)
