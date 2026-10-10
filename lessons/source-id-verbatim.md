---
triggers:
  - '\b(sync|pull|mirror|backup|archive|import|export|restore)\b.*\b(account|source|mail|gmail|drive|repo|bucket|dataset|device)\b'
  - '\b(mbsync|rclone|restic|rsync|imap|maildir|borg|chezmoi)\b'
  - '\b(channel|remote|profile|target) name\b'
  - '\bkeyed by\b'
  - '\bsource id\b'
---
[rule:source-id-verbatim] Specificity is first class: every source (Google account, device, bucket, repo, dataset) is keyed by its own UNCHANGEABLE native ID — the email, serial, UUID, canonical URL — used VERBATIM everywhere it appears: config entity names (channels/accounts/stores/profiles), directory paths, file names, CLI arguments, vault keys, log labels. NEVER invent a sanitized/mangled/derived variant (no `user_gmail_com`, no slugs, no hashes, no "friendly names"). If a tool's grammar seems to reject the raw ID, PROVE it with a live probe first — most accept it quoted — and only then discuss an escape hatch with the user; never silently substitute. One ID, one spelling, end to end.
