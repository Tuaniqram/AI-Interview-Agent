# Frontend Docs Index

Read before touching frontend code. These docs describe the repo as it is (versions pinned August 2026) plus upgrade notes for what changed upstream.

| Doc | Contents |
|---|---|
| `00-stack.md` | Version audit: installed vs latest, per-package risk, upgrade notes |
| `01-architecture.md` | Directory map, services/state/routing rules, naming, dead code list |
| `02-styling.md` | The three styling layers, token system map, Tailwind v3 discipline, quality floor |
| `03-build.md` | Dev server (port 3000), proxy, typecheck command, TS config, env vars |
| `04-motion-charts.md` | Framer Motion 12, Recharts 3, lucide 0.294, three.js/AuraCore rules |
| `05-testing.md` | Playwright e2e, manual verification checklist |
| `conventions.md` | Copywriting and code conventions for UI work |

## Maintenance rule

When a dependency is upgraded or a pattern changes, update the relevant doc in the same commit. An outdated doc here is worse than no doc: agents will trust it.
