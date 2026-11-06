# Styling System Map

The styling has three layers. Know which layer you are touching before changing any visual property.

## Layer 1: App-wide design tokens (the real system)

`frontend/src/assets/tailwind.css` defines all tokens as CSS variables on `:root` (light theme) and `[data-theme="dark"]`:

- Backgrounds: `--bg-page`, `--bg-section`, `--bg-elevated`, `--bg-input`, `--bg-hover`, `--bg-overlay`
- Text: `--text-primary/secondary/tertiary/muted/inverse`
- Lines: `--divider`, `--border-color`
- Actions: `--action-primary`, `--action-primary-hover`, `--action-danger`, `--action-disabled`, etc.
- Status: `--status-success/warning/error/info` (+ `-bg` and `-text` variants)
- Shadows: `--shadow-sm/md/lg`

`frontend/tailwind.config.js` maps them into Tailwind color names, so in JSX you write e.g. `bg-page text-primary border-border bg-action-primary`. Theme switching goes through `ThemeContext` toggling `data-theme` on the root.

**Default theme is LIGHT** (`--bg-page: #f5f5f7`). The dark glass look exists only where a component opts into it locally.

## Layer 2: Feature-scoped CSS namespaces

Some pages carry their own scoped stylesheet inside the component file, with prefixed class names and local variables:

| Namespace | Where | Notes |
|---|---|---|
| `el-*` + `--el-*` vars | `pages/Landing.tsx` | Self-contained dark-glass island; owns its own palette (`--el-accent`, `--el-glass-*`) |
| `al-*` | `components/auth/AuthLayout.tsx` | Auth shell |
| `ac-*` | `pages/AccountChoice.tsx` | Account chooser panel |
| aura.css | `components/AuraCore/` | 3D orb visuals |

When restyling one of these, change its namespace variables/classes; do not leak app tokens into it or vice versa until a deliberate unification pass.

## Layer 3: Tailwind utilities in JSX

Used by dashboard/org/candidate/hub pages and shared components (`components/shared/*`). Fonts come from `tailwind.config.js`: body = Open Sans, headings = Poppins, mono = JetBrains Mono (loaded in `index.html` from Google Fonts).

## Tailwind version discipline

This repo is **Tailwind v3**: `@tailwind base/components/utilities` directives, JS config file, `darkMode: ['selector', '[data-theme="dark"]']`.

Tailwind v4 (current upstream) removes the JS config in favor of CSS-first `@theme` blocks and renames directives to `@import "tailwindcss"`. Do NOT use v4 syntax here until an upgrade lands. Migration path when it happens: move the token bridge into `@theme { --color-page: var(--bg-page); ... }`; utility names mostly survive.

## Quality floor for any UI work

- Responsive down to mobile widths.
- Visible keyboard focus states (`:focus-visible`), never `outline: none` without replacement.
- Respect `prefers-reduced-motion` for non-essential animation.
- Contrast: text passes WCAG AA against its background.
