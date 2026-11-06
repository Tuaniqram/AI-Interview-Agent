# UI Conventions

Writing and code conventions for frontend work in this repo.

## Copywriting

- Sentence case everywhere ("Get started", "Real interviews"), never Title Case.
- Buttons name the action from the user's side: "Save changes" not "Submit"; "Run an interview" not "Go".
- No em dashes (user rule for user-facing copy). Use commas, colons, or periods.
- Errors state what happened and what to do next, in the interface's voice. No apologies, no vagueness.
- Empty states invite action: say what the screen is for and offer the first step.
- One term per concept through the whole flow: a "session" is never suddenly an "interview instance".

## Code

- Named exports; `export function Component()`.
- No default React import needed (`jsx: react-jsx`).
- Remove unused imports immediately; strict tsc fails on them.
- Tailwind utilities for app pages; feature-scoped CSS namespaces only where already established (`el-*`, `al-*`, `ac-*`).
- Colors/fonts/shadows always via tokens or namespace variables. Hardcoded hex values are allowed only inside a component's own scoped stylesheet that defines its variables.
- Comments only when asked or when genuinely non-obvious; no narration comments.

## Process

1. Read `docs/frontend/00-stack.md` before using any library API.
2. Typecheck after every meaningful change: `frontend\node_modules\.bin\tsc.cmd --noEmit -p frontend`.
3. Verify in both light and dark themes.
4. Never edit `src/data/realInterviews.ts` by hand.
