# Testing

## Playwright E2E (the only test suite)

- Config: `frontend/playwright.config.ts`; tests live in `frontend/tests/` (or `e2e/`), results in `frontend/test-results/`.
- Run: `npm run test:e2e` (headless) or `npm run test:e2e:ui` (interactive) from `frontend/`.
- The dev server must be running on port 3000, backend on 8000 for flows that hit APIs.

## Conventions

- Selectors: prefer `getByRole` / `getByText` over CSS selectors so tests survive styling passes.
- Auth-dependent tests should use the public routes or seeded accounts; do not depend on Google OAuth in CI.
- No unit test runner is configured. Do not add vitest/jest config without asking; component correctness is currently guarded by tsc strict mode + e2e.

## Manual verification checklist for UI changes

1. `tsc.cmd --noEmit -p frontend` clean.
2. Vite serves the changed module (`Invoke-WebRequest http://localhost:3000/src/...` returns 200).
3. Visual check on light theme AND dark theme (token system supports both).
4. Keyboard tab-through shows visible focus.
