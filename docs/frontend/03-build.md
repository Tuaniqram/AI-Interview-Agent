# Build, Dev Server, Typecheck

## Commands (run from repo root)

| Task | Command |
|---|---|
| Dev server | `npm run dev` in `frontend/` (serves on port 3000) |
| Typecheck | `frontend\node_modules\.bin\tsc.cmd --noEmit -p frontend` |
| Production build | `npm run build` in `frontend/` (runs tsc, then vite build) |
| E2E tests | `npm run test:e2e` in `frontend/` |

## Dev server facts

- Port is fixed at **3000** (`vite.config.ts`). On this machine Vite binds IPv6, so use `http://localhost:3000`, never `127.0.0.1`.
- Proxy to backend (`localhost:8000`): `/api` and `/interviews` (HTTP) and `/ws` (WebSocket, `ws: true`). Frontend code should call these relative paths in dev; absolute URLs only via `VITE_API_URL` for deploys.
- Heavy libs are split at build time via `manualChunks`: `vendor-three` (three), `vendor-charts` (recharts), `vendor-ui` (lucide-react). Keep new heavy dependencies out of the main chunk the same way.

## TypeScript config highlights (tsconfig.json)

- `"moduleResolution": "bundler"`, `"jsx": "react-jsx"` (no React import needed in files).
- Strict + `noUnusedLocals` + `noUnusedParameters`: unused imports fail the build, remove them.
- `noEmit: true`; typecheck and build are separate steps.
- Project references: `tsconfig.node.json` covers vite config itself.

## Environment variables

Only `VITE_`-prefixed vars are exposed to client code (`import.meta.env.VITE_API_URL`, `VITE_API_TIMEOUT`). Secrets never go here.

## Known gotchas

- Global `npx tsc` resolves to a bogus package on this machine; always use the local binary path above.
- After editing files, the CodeGraph index lags ~1s; PowerShell reads of UTF-8 files must use `[System.IO.File]::ReadAllText` with explicit encoding.
