---
triggers:
  - '\b(audit|inventory|stock-?take)\b'
  - '\bcritically (advise|assess|review)\b'
  - '\bwhat.?s (missing|not covered)\b'
  - '\bwhat am i missing\b'
  - '\b(be |get )?ruthless\b'
  - '\b(cut down|trim|prune|slim down)\b.*\b(services|stack|containers|tools)\b'
  - '\breview (my|our|the) (setup|stack|infra|homeserver|config)\b'
  - '\b(gaps?|blind spots?|weak links?)\b'
  - '\bdo i (even )?need\b'
---
[rule:evidence-discipline] Confident phrasing must not outrun the evidence actually gathered. Probing constantly is not the same as probing sufficiently — every rule below was broken in a session where dozens of live commands were run.

(1) AN ABSENCE CLAIM NEEDS A PROBE, EXACTLY LIKE A PRESENCE CLAIM. Before writing "nothing / no X / never / none of them" about the user's system, run the search that would have found it, and cite that command inline. Cost of breaking it: asserted "nothing verifies your backups" without ever opening the backup directory, which contained restore drills, sampled bit-rot re-reads, and sha256 cross-checks. This is the only true fabrication in that session, and it was a negative.

(2) ONE SAMPLE IS NOT A RATE. Never quote a number from the first sample of `docker stats`, `top`, `iostat`, `vmstat`. A GAUGE (memory, disk used) is fine on one read; a RATE (CPU %, IOPS, throughput) needs two. Cost: "the message broker burns 174% CPU permanently" from the first `docker stats --no-stream` sample; three clean samples showed ~1.2%. probe-guard.py now blocks this on Bash — but the same error through the Read tool is unguarded.

(3) A PEEK IS NOT A DISTRIBUTION. `head`/`tail`/`sed -n 'N,Mp'` characterize nothing. Aggregating a truncated input does not un-truncate it — `tail -c 2000 f | sort | uniq -c` is still 2000 bytes. Use `grep -o '<field>' f | sort | uniq -c | sort -rn` over the WHOLE file. Cost: "SIEM is just PAM login noise" from `tail -c 2000` of a 5.7 MB file; the real distribution was thousands of integrity-check events plus live file-integrity hits.

(4) READ THE ADJACENT LINE BEFORE CALLING SOMETHING A DEFECT. Cost: flagged plaintext OIDC client secrets as a security finding; three lines away, a comment recorded the deliberate decision and the condition under which to revisit it.

(5) REASON FROM BEHAVIOUR YOU OBSERVED, NOT FROM THE CATEGORY THE THING BELONGS TO. "A second metrics agent, therefore redundant" was wrong: they sample at different intervals for different purposes. They answer different questions. Membership in a category predicts nothing; measure it.

When cutting or condemning something the user built, separate USE from VALUE from CORRECTNESS. Page views measure use — a watchdog, a backup daemon and a CA correctly have zero. And "unused" is a different verdict from "broken": check which one you are looking at before recommending deletion.
