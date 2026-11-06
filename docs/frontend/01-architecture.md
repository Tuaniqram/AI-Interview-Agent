# Architecture and Conventions

How this frontend is actually organized. Follow these patterns; do not invent new ones.

## Directory map (frontend/src)

| Dir | Purpose | Examples |
|---|---|---|
| `routes/` | Route definitions, one file per route group + `index.tsx` | `index.tsx`, `BrainGraphPage.tsx` |
| `pages/` | Full-page screens grouped by role | `Landing.tsx`, `auth/Login.tsx`, `org/AdminDashboard.tsx`, `candidate/Dashboard.tsx`, `hub/OpportunityHubHome.tsx` |
| `components/` | Shared + feature components | `shared/Button.tsx`, `graph/BrainGraph.tsx`, `AuraCore/` |
| `contexts/` | React contexts | `AuthContext.tsx`, `CandidateAuthContext.tsx`, `OrgContext.tsx`, `ThemeContext.tsx` |
| `services/` | API layer, one service per backend domain | `apiClient.ts`, `interviewService.ts`, `authService.ts` |
| `hooks/` | Reusable hooks | `useCamera.ts`, `useVoice.ts`, `useDebounce.ts` |
| `controllers/` | Imperative controllers for complex widgets | interview room logic |
| `data/` | Static/embedded data modules | `realInterviews.ts` (AUTO-GENERATED), `brainSnapshots.ts` |
| `types/` | Shared TS types | `api.ts` |
| `utils/` | Pure helpers | token storage, formatting |
| `styles/`, `assets/` | Global CSS | `assets/tailwind.css`, `styles/datepicker.css` |

## Rules

1. **API access only through services.** Components never call axios/fetch directly (`apiClient.ts` header says so). Add a method to the relevant `*Service.ts` instead. The client attaches `Authorization: Bearer` and `X-Org-Id` headers automatically and refreshes on 401.
2. **Auth is split by persona**: org-side state in `AuthContext`, candidate-side in `CandidateAuthContext`. Guards: `ProtectedRoute.tsx` (org) and `ProtectedCandidateRoute.tsx` (candidate).
3. **Routing** is declarative `<Routes>` in `src/routes/index.tsx`. Public marketing routes (`/`, `/account`) sit outside guards.
4. **Backend base URL**: dev uses the Vite proxy (`/api`, `/interviews`, `/ws` -> `localhost:8000`, see `vite.config.ts`). `VITE_API_URL` env var overrides for prod builds.
5. **Generated data**: `src/data/realInterviews.ts` is produced by a Python script from real sessions. Never hand-edit it; regenerate instead.
6. **WebSocket** interviews go through `services/interviewWebSocket.ts`, not raw `new WebSocket()` in components.

## Naming

- Components: `PascalCase.tsx`, one main export per file, named exports preferred.
- Hooks: `useXxx.ts`. Services: `xxxService.ts`. Contexts: `XxxContext.tsx` exporting both provider and hook.
- CSS: Tailwind utilities in JSX; component-scoped plain CSS classes are prefixed per feature (e.g. Landing uses `el-*`, auth layout uses `al-*`, account choice `ac-*`).

## Known dead code (do not copy patterns from)

`pages/marketing/` (`Hero`, `Testimonials`, `UseCases`, `Stats`, `ProcessFlow`, `LangGraphFlow`, `AnimatedFlow`, `Features`, `FAQ`, `CTASection`) and `pages/Landing.old.tsx` have zero imports anywhere. They are scheduled for deletion and must not be used as references.
