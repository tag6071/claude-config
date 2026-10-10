---
triggers:
  - '\b(explain|explanation|document|documentation|write[- ]?up|readme|guide|runbook|bootstrap)\b'
  - '\b(concise|brief|terse|to the point|occam)\b'
  - '\b(new|another) (doc|file|markdown|md)\b'
  - 'too (long|much|verbose|wordy)'
  - 'dump(ing|ed)? (info|information|a textbook)'
  - 'fold (it |this )?(in|into)'
  - '\b(link|linkable|clickable|anchor|hyperlink)\b'
  - '§[0-9]'
---
[rule:concise-fold-first] When writing prose OR docs (always):

DON'T DUMP. Lead with the answer/command. The user is here to ship, not to read a
textbook — hours spent reading docs is hours not coding (an anti-pattern).
- Answer first sentence = the result, command, or decision. No preamble, no recap.
- Tables/bullets over paragraphs for anything ≥3 items. Occam's razor: simplest
  form that's still correct + specific. Cut, don't append.
- High signal, zero filler. If a sentence doesn't change what the user does next,
  delete it. A risk/caveat is ONE clause, not a paragraph.

FOLD, DON'T SPAWN. Before creating any new doc:
1. Grep/list existing docs in that subsystem first (the doc-guard hook pauses the
   first new doc-like write in a repo, hard-blocks any new file outside one, and shows you the fold candidates — heed it).
2. Default = extend the closest existing doc. A new file needs a real reason
   (distinct audience, distinct lifecycle) stated out loud — not "it's cleaner."
3. Less documentation is better. One lean machine-tagged runbook beats two
   overlapping ones.

CLICKABLE REFS, not code-span noise. A reference to another file OR a section is a
real link, never bare text or a code-span:
- file → [name](relative/path) — verify the relative path resolves from THIS doc.
- section → [§N](#slug); slug = heading lowercased, punctuation/emoji dropped,
  spaces→hyphens. So keep headings slug-safe (no emoji/parens/em-dash in heading
  text — move tags to a body line).
- keep code-spans ONLY for commands, flags, device names, values, globs, gitignored
  files. Fix every ref in ONE pass across the whole doc, never one at a time.

Enforcement: doc-guard.py blocks new-file sprawl (any type) AND non-clickable refs (bare §N /
resolving `*.md` code-spans). Prose verbosity is on YOU — no hook measures wordiness.
Pairs: terse output style.
