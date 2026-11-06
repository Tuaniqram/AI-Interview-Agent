# Frontend Stack Audit

Verified against the npm registry on 2026-08-21. "Installed" = what `frontend/package.json` pins today. Read this before writing any frontend code so you use the APIs this repo actually has, not the ones from training data.

## Version table

| Package | Installed | Latest (2026-08) | Risk if you assume latest |
|---|---|---|---|
| react / react-dom | ^18.2.0 | 19.2.8 | HIGH: no `use()` hook, no Actions, no `ref` as prop, different types |
| react-router-dom | ^6.30.4 | 7.18.2 | HIGH: v7 changed imports (`react-router` package), data routers default |
| vite | ^5.0.8 | 8.2.2 | MEDIUM: Vite 6/7/8 changed env handling and defaults |
| typescript | ^5.2.2 | 7.0.2 | MEDIUM: TS 6/7 (native port) changes CLI flags; repo uses classic tsc 5.x |
| tailwindcss | ^3.3.6 | 4.3.3 | HIGH: v4 is CSS-first, no `tailwind.config.js`, new engine, different directives |
| lucide-react | ^0.294.0 | 1.33.0 | LOW-MED: icon names mostly stable; some icons added/renamed since 0.294 |
| framer-motion | ^12.43.0 | 13.1.1 (now `motion`) | MED: package renamed to `motion`, import paths differ in v13+ |
| recharts | ^3.9.2 | 3.10.1 | NONE: current |
| three | ^0.185.1 | 0.185.1 | NONE: current |
| axios | ^1.6.2 | 1.19.0 | LOW |
| @playwright/test | ^1.61.1 | 1.62.1 | NONE: current |
| @vitejs/plugin-react | ^4.2.1 | 6.1.0 | LOW |
| @react-oauth/google | ^0.13.5 | 0.13.5 | NONE: current |
| react-datepicker | ^9.1.0 | 9.1.0 | NONE: current |

## Rules that follow from this

1. **React 18 semantics only.** Use `ReactDOM.createRoot` (already in `src/main.tsx`). Do not use React 19-only APIs (`use()`, server actions, `useOptimistic`, ref-as-prop). Forward refs via `forwardRef`.
2. **react-router v6 API only.** Routes live in `src/routes/index.tsx` using `<Routes>/<Route>` + `createBrowserRouter`-free declarative style. Imports come from `'react-router-dom'`, never `'react-router'`. Loader/action data APIs are not configured here.
3. **Tailwind v3 syntax only.** Config is `frontend/tailwind.config.js` with `@tailwind base/components/utilities` in `src/assets/tailwind.css`. No `@import "tailwindcss"`, no `@theme`, no CSS-first config.
4. **Framer Motion v12 imports**: `import { motion, AnimatePresence } from 'framer-motion'`. The `motion/react` import path belongs to the newer `motion` package; do not use it here.
5. **TypeScript strict mode** is on (`strict`, `noUnusedLocals`, `noUnusedParameters`). Code must pass: `frontend\node_modules\.bin\tsc.cmd --noEmit -p frontend`.

## Upgrade notes (for a future upgrade session)

- React 19: codemod available (`npx codemod-react-19`); main breaks are removed string refs/propTypes, `ReactDOM.render` gone, types package split.
- Router v7: mostly additive over v6 data routers; this repo would need `createBrowserRouter` migration first.
- Tailwind v4: replaces config JS with `@theme` in CSS; the token bridge in `tailwind.config.js` (colors mapped to CSS vars) ports naturally but every utility stays.
- Vite 8: check proxy syntax and `manualChunks` (may move to `advancedChunks`); env var prefix unchanged (`VITE_`).
