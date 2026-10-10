---
triggers:
  - '\b(download|fetch|stage|pull|mirror)\b.*\b(iso|image|installer|artifact|firmware|apk)\b'
  - '\b(iso|installer|image)\b.*\b(usb|flash|mount|kvm|serve)\b'
  - '\b(stage|staged|staging)\b.*\bon (homeserver|the remote|another box)\b'
---
[rule:target-first-staging] Stage artifacts on the box that CONSUMES them. Before running any task that downloads/stages/mutates on a remote machine, name out loud: (1) which box the artifact is actually consumed on, (2) where the task's side effects land. They must match — if not, don't run the task; do the direct thing (consumer = Mac → download to the Mac). A task existing is not a reason to use it ("a task stages ISOs" ≠ "that box is where this install needs the image"); routing through a second box adds a copy hop and leaves junk on a machine that never needed it. AND: verify scoping args are actually honored by the task before trusting them — a silently-ignored filter (e.g. `-e filter=X` passed to a script that reads `$1`) turns a scoped fetch into a bulk mutation of the whole manifest. Negative-test: would the task's output/duration look different if the filter worked? Example: a scoped fetch silently ignored its filter and pulled a 10 GB manifest onto a server when the image was only needed on the laptop.
