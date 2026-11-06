# Motion, Charts, Icons, 3D

## Framer Motion 12

Import from `'framer-motion'` (NOT `motion/react`; that is the v13+ package name this repo does not use).

Used for: page transitions, list staggers, presence animations. Patterns in repo: `AnimatePresence` for mount/unmount, `motion.div` with `initial/animate/exit`, variants objects.

Rules:
- Wrap decorative animation in `useReducedMotion()` checks or CSS `@media (prefers-reduced-motion)`.
- Keep durations 0.2-0.35s for UI feedback; longer only for orchestrated hero moments.

## Recharts 3

Current version. Used in dashboards (`ScoreDistribution.tsx`, `CompetencyRadar.tsx`). Charts must read colors from the token system (`var(--status-success)` etc. via computed style or Tailwind palette names), not hardcoded hexes, so they survive theme switches. Bundle is isolated in the `vendor-charts` chunk; import recharts only inside chart components.

## Lucide icons 0.294

`import { Brain, GitBranch } from 'lucide-react'`. Icon set is older than upstream: if an icon does not exist, check the installed version's exports before adding a dependency or faking one with SVG. Common pattern: `<Icon size={17} strokeWidth={2.2} />`.

## Three.js 0.185

Only used by `components/AuraCore/` (orb visuals: ParticleField, OrbitalRing, PlasmaNucleus, ScanningArc, SegmentRing, EnergyPulse, GlowLayer). Conventions:
- All three.js code stays inside AuraCore; pages consume ready-made components.
- Render loops must clean up on unmount (dispose geometries/materials, cancel animation frames).
- Chunked as `vendor-three`; never import three outside AuraCore.
- These components are decoration candidates for the de-slop pass; do not add new instances elsewhere.

## React DatePicker 9 + @react-oauth/google 0.13

DatePicker styles are overridden in `src/styles/datepicker.css`; Google OAuth provider wraps the app at `main.tsx` level. Use existing wrappers instead of new OAuth flows.
