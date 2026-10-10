---
triggers:
  - '\bnuke\b'
  - 'completely (remove|uninstall|purge|wipe)'
  - '(good|safe|ok) to push|push (it |this )?to (the )?remote|should i push'
  - 'design system|inconsisten|spacing'
  - 'make this (an? )?(rr )?command|rr-?ify'
  - 'self.?hosted git|git service|push (it|this|the (code|repo|codebase))|(create|new|make) (a |the )?(git )?repo'
---
[rule:skill-first] A custom skill exists for this — invoke it via the Skill tool instead of improvising: purge an app → /nuke; "safe/good to push?" → /push-audit (answer-only, never pushes); UI consistency/spacing sweep → /design-sweep; wrap a manual step into an rr task → /rr-ify. The skill IS the house procedure; an ad-hoc version that skips its ritual steps is a defect. New repo → run `gitleaks detect --redact` FIRST (gate) before creating any remote. Before improvising ANY ops step, check the repo's task runner list (e.g. `rr --list`) and your scripts README — the user built a command for it more often than not.
