---
triggers:
  - 'new (sub)?(module|subsystem)|add(ing)? (a )?(new )?(sub)?(module|subsystem)'
  - "not (fully |100% )?iac|isn'?t iac|can'?t be iac|cannot be iac|partly iac|partial iac"
  - 'manual step|by hand|in the (gui|web ?ui|ui)|human(-| )in(-| )the(-| )loop|hitl'
  - 'bootstrap (the|this|a|new)|readme-bootstrap'
  - 'runbook|hand ?off|cutover|migration|self[- ]serve|without (you|claude|ai)|do (it|them|this) myself'
  - 'open (the |a |up )?port|expose|bypass|hardcod|plaintext|just make it work|disable .*(auth|security|check|hook|valid)|skip .*(auth|verif|valid)'
  - 'secret|password|passphrase|credential|api[ _-]?key|\btoken\b|seed (a|the|new)'
  - '\bautomat|\biac\b|terraform|ansible|pulumi|playbook|provision'
  - '\bcron\b|scheduled? (job|task)'
  - 'script (this|it|that)|make (this|it) rerunnable'
---
# HITL+ — exhaust IaC, then make the human SELF-SUFFICIENT (not dependent on me)

## GATE LADDER — a human step is irreducible ONLY after all 4 fail. Name each + evidence.
| # | Try this first | Evidence it's truly impossible |
|---|----------------|--------------------------------|
| 1 | device REST/JSON API (router/firewall API, DNS appliance API, AP config JSON) | probed → 404 / no write path |
| 2 | script / protocol shim (vendor protocol shim, Ansible module) | none exists + not cheaply writable |
| 3 | headless flag / config-file path INSTEAD of the GUI | GUI-only, no unattended path |
| 4 | secret → generate-and-vault · file/command → do-it-myself | only a human-TYPED value remains |

Passed all 4 → irreducible. Failed any → **automate it, there is no human step.**

## IRREDUCIBLE = EXACTLY ONE OF THESE. Nothing else counts.
- 🔌  physical: cable / button / power
- ⌨️   a secret VALUE I must never see (user types or pastes it)
- 🧠  a genuine decision

## OUTPUT CONTRACT — every runbook / BOOTSTRAP / handoff doc I write
Every step is ONE of two glyphs. **There is no third.**
- 🧑  irreducible (one of the three above)
- 🖥  a NAMED command (`rr …` / playbook / script) — anyone runs it, **AI optional**

**BANNED in any handoff doc:** `🤖`, "Claude drives", "I'll run it", "ask Claude", "I drive/handle the …", or any step that needs me. If I *can* run it, the USER can too → write the command, not my name.

## SPECIFICITY — a 🧑 step is NEVER a verb-noun ("install the firewall OS", "flash the SSD", "set up the box")
That is a HEADING, not a step. Expand EVERY 🧑 step into the literal sequence a stranger could follow blind:
- exact artifact + where: download URL / filename / version (`<os>-<version>-amd64.iso` from the vendor's download page)
- exact tool + command: which flasher (`balenaEtcher` / `dd if=… of=/dev/diskN bs=1m`), which port, which key to hold at boot
- the literal choices: every menu/prompt → the exact option to pick ("Installer login: `<user>` / `<password>`" → "ZFS" → "stripe" → pick the target disk)
- expected result after each: "screen shows the WAN interface up with an address" — so the user KNOWS it worked before moving on
- the failure branch: "if X doesn't appear → do Y"

**Self-serve test before shipping a runbook:** hand it to someone who has never seen this setup and is offline — can they finish start-to-end without one guess or one question to me? No → it is NOT done. Banned handoff words: "install", "set up", "configure", "flash" standing ALONE with no sub-steps. The only judgment step allowed is a `*-diff` review, with its decision rule written inline.

## SECRETS (mechanism — never improvise)
- live in `<module>/secrets.yml` (git-ignored) + committed `<module>/secrets.yml.example` manifest (every key + purpose)
- mintable: `uv run rr secret-new <var> <module>/secrets.yml [bytes]` → generate, SHOW once, they run it, I never see it
- external/pasted: scaffold key in `secrets.yml` + `.example` → they type the value → `rr vault-encrypt`
- NEVER: loose in `group_vars` · ad-hoc `openssl | encrypt_string` · "you invent + paste it"

## SECURITY VETO — overrides everything above. The manual step STAYS before any of these.
Removing a human step must NEVER:
- expose / log / echo / commit a secret
- open a raw port · SSO/auth bypass · publish off `127.0.0.1`
- disable / skip a control, validation, or hook
- broaden privilege (no `NOPASSWD` on the interactive user — `ansible` user only)
- weaken TLS / encryption / cert validation

"Can't automate without weakening security" IS a valid irreducible reason — the **5th gate, a veto.** Surface + document.
Server security floor (example): edge-only `:443` + SSO · loopback-only publish · vaulted secrets · dedicated automation user. Touch one → STOP-and-surface.

## CODIFY BEFORE EXECUTE — the artifact IS the deliverable
Automation/IaC/repeatable-ops work: write the NAMED rerunnable artifact (script / playbook / module — shape per [scripts.md](../playbook/scripts.md)) FIRST, then run THAT. Ad-hoc execution of codifiable work is a defect **even when I run it myself** — the user must be able to rerun it without AI; there must be an IT to run. Truly one-off + trivial (single obvious command, nothing to parameterize) → execute directly, say so in one clause.

Pairs: [persist-gate.py](../hooks/persist-gate.py).
