---
triggers:
  - '\b(form|forms|input|field|fields|textbox|text field)\b'
  - '\b(validat|invalid|required field|error message)\b'
  - '\b(submit|submission|sign ?up|sign ?in|log ?in|login|register|registration)\b'
  - '\b(checkout|wizard|stepper|multi-?step|onboarding|data entry)\b'
---
[rule:forms-bulletproof] Forms are make-or-break — build them bulletproof every time, no exceptions, and never reinvent what the stack already solves.

LIBRARY (locked, not reinvention): react-hook-form + zod + @hookform/resolvers + shadcn `<Form>`. Use the scaffold's `<AppForm>`/`useZodForm` primitive — never hand-roll a `<form>` + useState, never add formik/final-form. Selects/dialogs/comboboxes IN forms = shadcn (Radix), never native `<select>` or a custom overlay (they ship focus-trap + aria-modal + Escape/restore-focus you'd otherwise get wrong).

VALIDATE BOTH SIDES, ALWAYS: client zod (instant inline feedback) AND server (the real gatekeeper — never trust the client). Same rules, derived from the one OpenAPI contract; on a Go backend the handler must reject bad input with 400 before using it.

BAKED-IN UX (the shadcn `<Form>` + `<AppForm>` give most of this — don't drop it):
- Submit disabled while invalid OR submitting; shows a pending/spinner state; guard against double-submit.
- Per-field inline errors wired for a11y (label assoc, aria-invalid, aria-describedby — shadcn Form does this).
- Mutation failure → toast (sonner); success → toast or inline confirmation. Loading + empty + error states are designed.
- Multi-step flows CANNOT advance past an invalid step. Destructive actions confirm via a shadcn Dialog. Optimistic updates only where safe to roll back.

ERGONOMICS: fewest fields, sensible defaults pre-filled, sane input types/inputmode, auto-advance on single-choice where it saves a tap. See [[ui-design-baseline]].
