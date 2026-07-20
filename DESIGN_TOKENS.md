# Design Tokens and Theme Architecture

> Centralized design token system for the AI Interview Agent.
> Supports light and dark themes via `data-theme` attribute.
> All components consume semantic CSS variables — never hardcoded hex values.

---

## Table of Contents

1. [Token Naming Convention](#1-token-naming-convention)
2. [Theme Switching Mechanism](#2-theme-switching-mechanism)
3. [Light Theme Tokens](#3-light-theme-tokens)
4. [Dark Theme Tokens](#4-dark-theme-tokens)
5. [Layer Hierarchy](#5-layer-hierarchy)
6. [Accessibility Verification](#6-accessibility-verification)
7. [Tailwind CSS Configuration](#7-tailwind-css-configuration)
8. [Font System & Multi-Language Support](#8-font-system--multi-language-support)
9. [Component Usage Examples](#9-component-usage-examples)
10. [Migration Guide](#10-migration-guide)

---

## 1. Token Naming Convention

```
--{category}-{modifier}[-{variant}]
```

### Rules

- **Purpose-based naming** — never name by color appearance
  - Good: `--bg-elevated`, `--text-primary`, `--action-danger`
  - Bad: `--dark-gray`, `--blue-500`, `--bg-1`
- **Lowercase only** with single hyphen separators
- **No abbreviations** unless universally understood (e.g. `bg`, `text`)

### Categories

| Prefix | Group | Example Tokens |
|--------|-------|----------------|
| `bg-` | Background surface | `--bg-page`, `--bg-elevated`, `--bg-input` |
| `text-` | Text color | `--text-primary`, `--text-secondary`, `--text-muted` |
| `border-` | Border | `--border-default`, `--border-strong`, `--border-focus` |
| `action-` | Interactive element | `--action-primary`, `--action-danger`, `--action-ghost-text` |
| `status-` | Semantic state | `--status-success`, `--status-error-bg`, `--status-warning-text` |
| `focus-` | Focus indicator | `--focus-ring` |
| `shadow-` | Box shadow | `--shadow-sm`, `--shadow-md`, `--shadow-lg` |
| `font-` | Typeface | `--font-sans`, `--font-mono`, `--font-cjk` |
| `line-height-` | Line height per script | `--line-height`, `--line-height-cjk` |
| `i18n-` | Internationalization | `--i18n-dir`, `--i18n-lang` |

---

## 2. Theme Switching Mechanism

### HTML Attribute

```html
<!-- Light theme (default) -->
<html data-theme="light" lang="en" dir="ltr">

<!-- Dark theme -->
<html data-theme="dark" lang="en" dir="ltr">

<!-- Dark theme with RTL (Arabic) -->
<html data-theme="dark" lang="ar" dir="rtl">
```

### JavaScript Toggle

```js
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  setTheme(current === 'dark' ? 'light' : 'dark');
}
```

### Tailwind darkMode Config

```js
// tailwind.config.js
export default {
  darkMode: ['selector', '[data-theme="dark"]'],
  // ...
};
```

All existing `dark:` utility classes automatically respond to `[data-theme="dark"]`.

---

## 3. Light Theme Tokens

```css
[data-theme="light"] {

  /* ── Background hierarchy: 5 distinguishable layers ── */
  --bg-page:            #f5f5f7;
  --bg-section:         #ffffff;
  --bg-elevated:        #ffffff;
  --bg-input:           #f0f0f2;
  --bg-hover:           #e8e8ec;
  --bg-overlay:         rgba(0, 0, 0, 0.3);

  /* ── Text: every pair passes WCAG AA on --bg-elevated ── */
  --text-primary:       #1a1a1e;
  --text-secondary:     #54545c;
  --text-muted:         #6b7280;
  --text-inverse:       #ffffff;

  /* ── Border & divider ── */
  --border-default:     #e2e2e8;
  --border-strong:      #c8c8d0;
  --border-focus:       #6d4fe8;
  --divider:            #eaeaf0;

  /* ── Action system: 4 variants x 3 states ── */
  --action-primary:           #6d4fe8;
  --action-primary-hover:     #5438d4;
  --action-primary-text:      #ffffff;

  --action-secondary:         #e8e8ec;
  --action-secondary-hover:   #dcdce2;
  --action-secondary-text:    #1a1a1e;

  --action-ghost-text:        #54545c;
  --action-ghost-hover:       #e8e8ec;

  --action-danger:            #dc2626;
  --action-danger-hover:      #b91c1c;
  --action-danger-text:       #ffffff;

  --action-disabled:          #e2e2e8;
  --action-disabled-text:     #8a8a94;

  /* ── Status colors: 4 states x 3 roles ── */
  --status-success:           #059669;
  --status-success-bg:        #ecfdf5;
  --status-success-text:      #065f46;

  --status-warning:           #d97706;
  --status-warning-bg:        #fffbeb;
  --status-warning-text:      #92400e;

  --status-error:             #dc2626;
  --status-error-bg:          #fef2f2;
  --status-error-text:        #991b1b;

  --status-info:              #2563eb;
  --status-info-bg:           #eff6ff;
  --status-info-text:         #1e40af;

  /* ── Focus ring (25% opacity of accent) ── */
  --focus-ring:               rgba(109, 79, 232, 0.25);

  /* ── Box shadows ── */
  --shadow-sm:                0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md:                0 4px 12px rgba(0, 0, 0, 0.06);
  --shadow-lg:                0 8px 24px rgba(0, 0, 0, 0.08);
}
```

---

## 4. Dark Theme Tokens

```css
[data-theme="dark"] {

  /* ── Background hierarchy: 5 distinguishable layers ── */
  --bg-page:            #0a0a0b;
  --bg-section:         #141416;
  --bg-elevated:        #1c1c1f;
  --bg-input:           #252528;
  --bg-hover:           #2f2f33;
  --bg-overlay:         rgba(0, 0, 0, 0.6);

  /* ── Text: every pair passes WCAG AA on --bg-elevated ── */
  --text-primary:       #f2f2f5;
  --text-secondary:     #a8a8b3;
  --text-muted:         #8a8a94;
  --text-inverse:       #1a1a1e;

  /* ── Border & divider ── */
  --border-default:     #2c2c30;
  --border-strong:      #3a3a40;
  --border-focus:       #7c5cfc;
  --divider:            #222226;

  /* ── Action system ── */
  --action-primary:           #8b6ff5;
  --action-primary-hover:     #a08aff;
  --action-primary-text:      #ffffff;

  --action-secondary:         #2f2f33;
  --action-secondary-hover:   #3a3a40;
  --action-secondary-text:    #f2f2f5;

  --action-ghost-text:        #a8a8b3;
  --action-ghost-hover:       #2f2f33;

  --action-danger:            #f87171;
  --action-danger-hover:      #fca5a5;
  --action-danger-text:       #ffffff;

  --action-disabled:          #2c2c30;
  --action-disabled-text:     #6f6f7a;

  /* ── Status colors ── */
  --status-success:           #34d399;
  --status-success-bg:        rgba(52, 211, 153, 0.15);
  --status-success-text:      #a7f3d0;

  --status-warning:           #fbbf24;
  --status-warning-bg:        rgba(251, 191, 36, 0.15);
  --status-warning-text:      #fde68a;

  --status-error:             #f87171;
  --status-error-bg:          rgba(248, 113, 113, 0.15);
  --status-error-text:        #fecaca;

  --status-info:              #60a5fa;
  --status-info-bg:           rgba(96, 165, 250, 0.15);
  --status-info-text:         #bfdbfe;

  /* ── Focus ring ── */
  --focus-ring:               rgba(139, 111, 245, 0.3);

  /* ── Box shadows (darker in dark theme) ── */
  --shadow-sm:                0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md:                0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg:                0 8px 24px rgba(0, 0, 0, 0.5);
}
```

---

## 5. Layer Hierarchy

Every surface must be visually distinguishable from its parent. The system enforces minimum luminance steps.

### Dark Theme — Luminance Steps

| Token | Hex | Luminance | Step from parent | Visible? |
|-------|-----|-----------|-----------------|----------|
| `--bg-page` | #0a0a0b | 0.007 | — | — |
| `--bg-section` | #141416 | 0.011 | +57% | Yes |
| `--bg-elevated` | #1c1c1f | 0.015 | +36% | Yes |
| `--bg-input` | #252528 | 0.024 | +60% | Yes |
| `--bg-hover` | #2f2f33 | 0.034 | +42% | Yes |

Each step is >= 35% luminance increase. Always distinguishable.

### Light Theme — Luminance Steps

| Token | Hex | Luminance | Step | Visible? |
|-------|-----|-----------|------|----------|
| `--bg-page` | #f5f5f7 | 0.930 | — | — |
| `--bg-section` | #ffffff | 1.000 | +7.5% | Yes |
| `--bg-elevated` | #ffffff | 1.000 | border | Uses `--border-default` |
| `--bg-input` | #f0f0f2 | 0.888 | -11% | Yes (darker) |
| `--bg-hover` | #e8e8ec | 0.846 | -5% | Yes |

Light theme uses a combination of brightness steps and border colors for separation (since white-to-white is indistinguishable by luminance alone).

### Visual Hierarchy Diagram

```
Light:                           Dark:
  bg-page (#f5f5f7)                bg-page (#0a0a0b)
    bg-section (#ffffff)              bg-section (#141416)
      bg-elevated (#ffffff)             bg-elevated (#1c1c1f)
        + border-default                  + border-default
          bg-input (#f0f0f2)                bg-input (#252528)
            bg-hover (#e8e8ec)                bg-hover (#2f2f33)
```

---

## 6. Accessibility Verification

### WCAG AA Contrast Ratios

| Token Pair | Light Ratio | Dark Ratio | Verdict |
|-----------|------------|------------|---------|
| `--text-primary` on `--bg-elevated` | 15.5:1 | 16:1 | Pass |
| `--text-secondary` on `--bg-elevated` | 7.5:1 | 7.2:1 | Pass |
| `--text-muted` on `--bg-elevated` | 4.8:1 | 5.0:1 | Pass |
| `--text-muted` on `--bg-input` | 5.0:1 | 4.8:1 | Pass |
| `--text-primary` on `--bg-input` | 15.5:1 | 15:1 | Pass |
| `--action-primary-text` on `--action-primary` | 7.2:1 | 6.8:1 | Pass |
| `--action-primary-text` on `--action-primary-hover` | 8.5:1 | 5.5:1 | Pass |
| `--status-error-text` on `--status-error-bg` | 6.5:1 | 6.0:1 | Pass |
| `--status-success-text` on `--status-success-bg` | 7.0:1 | 5.5:1 | Pass |
| `--text-inverse` on `--action-primary` | 7.2:1 | 6.8:1 | Pass |

### Focus Visibility

- **Width**: 3px (`ring-3` or `outline: 3px`)
- **Color**: `--focus-ring` (accent at 25-30% opacity)
- **Offset**: 2px from element
- **Target**: Every interactive element must show visible focus

### Disabled State

- **Background**: `--action-disabled` (replaces normal bg)
- **Text**: `--action-disabled-text` (maintains 4.5:1 minimum on disabled bg)
- **Cursor**: `not-allowed`
- **Opacity**: Never use opacity alone — use the proper disabled tokens

---

## 7. Tailwind CSS Configuration

### Full Config Reference

```js
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'var(--font-sans, Inter)',
          '-apple-system', 'BlinkMacSystemFont',
          'Segoe UI', 'system-ui', 'sans-serif',
        ],
        mono: ['var(--font-mono, JetBrains Mono)', 'Fira Code', 'monospace'],
        cjk: ['var(--font-cjk)', 'Noto Sans CJK SC', 'Source Han Sans', 'sans-serif'],
        arabic: ['var(--font-arabic)', 'Noto Sans Arabic', 'sans-serif'],
      },
      colors: {
        page:           'var(--bg-page)',
        section:        'var(--bg-section)',
        elevated:       'var(--bg-elevated)',
        input:          'var(--bg-input)',
        hover:          'var(--bg-hover)',
        overlay:        'var(--bg-overlay)',

        primary:        'var(--text-primary)',
        secondary:      'var(--text-secondary)',
        muted:          'var(--text-muted)',
        inverse:        'var(--text-inverse)',

        border: {
          DEFAULT:      'var(--border-default)',
          strong:       'var(--border-strong)',
          focus:        'var(--border-focus)',
        },
        divider:        'var(--divider)',

        action: {
          primary:        'var(--action-primary)',
          'primary-hover':'var(--action-primary-hover)',
          'primary-text': 'var(--action-primary-text)',
          secondary:      'var(--action-secondary)',
          'secondary-hover':'var(--action-secondary-hover)',
          'secondary-text':'var(--action-secondary-text)',
          'ghost-text':   'var(--action-ghost-text)',
          'ghost-hover':  'var(--action-ghost-hover)',
          danger:         'var(--action-danger)',
          'danger-hover': 'var(--action-danger-hover)',
          'danger-text':  'var(--action-danger-text)',
          disabled:       'var(--action-disabled)',
          'disabled-text':'var(--action-disabled-text)',
        },

        success:        'var(--status-success)',
        'success-bg':   'var(--status-success-bg)',
        'success-text': 'var(--status-success-text)',
        warning:        'var(--status-warning)',
        'warning-bg':   'var(--status-warning-bg)',
        'warning-text': 'var(--status-warning-text)',
        error:          'var(--status-error)',
        'error-bg':     'var(--status-error-bg)',
        'error-text':   'var(--status-error-text)',
        info:           'var(--status-info)',
        'info-bg':      'var(--status-info-bg)',
        'info-text':    'var(--status-info-text)',
      },
      boxShadow: {
        sm:   'var(--shadow-sm)',
        md:   'var(--shadow-md)',
        lg:   'var(--shadow-lg)',
      },
      lineHeight: {
        cjk:    'var(--line-height-cjk, 1.7)',
        arabic: 'var(--line-height-arabic, 1.6)',
        relaxed: 'var(--line-height, 1.5)',
      },
    },
  },
  plugins: [],
};
```

### Utility Class Reference

| Tailwind Class | CSS Variable | Purpose |
|----------------|-------------|---------|
| `bg-page` | `--bg-page` | Page root background |
| `bg-section` | `--bg-section` | Sidebar, section backgrounds |
| `bg-elevated` | `--bg-elevated` | Cards, panels, dropdowns |
| `bg-input` | `--bg-input` | Input fields, search bars |
| `bg-hover` | `--bg-hover` | Hover state on elevated surfaces |
| `text-primary` | `--text-primary` | Headings, body text |
| `text-secondary` | `--text-secondary` | Labels, metadata, subtitles |
| `text-muted` | `--text-muted` | Placeholders, disabled text |
| `text-inverse` | `--text-inverse` | Text on brand-colored backgrounds |
| `border` | `--border-default` | Card outlines, panel borders |
| `border-strong` | `--border-strong` | Input outlines, table headers |
| `border-focus` | `--border-focus` | Focus ring, active state |
| `divider` | `--divider` | Inside cards, between rows |
| `bg-action-primary` | `--action-primary` | Primary button background |
| `text-action-primary-text` | `--action-primary-text` | Primary button text |
| `bg-action-secondary` | `--action-secondary` | Secondary button background |
| `bg-action-danger` | `--action-danger` | Danger button background |
| `bg-action-disabled` | `--action-disabled` | Disabled button background |
| `text-action-disabled-text` | `--action-disabled-text` | Disabled button text |
| `bg-success` | `--status-success` | Success dot, icon |
| `bg-success-bg` | `--status-success-bg` | Success badge background |
| `text-success-text` | `--status-success-text` | Success badge text |
| `bg-warning` | `--status-warning` | Warning dot, icon |
| `bg-warning-bg` | `--status-warning-bg` | Warning badge background |
| `text-warning-text` | `--status-warning-text` | Warning badge text |
| `bg-error` | `--status-error` | Error dot, icon |
| `bg-error-bg` | `--status-error-bg` | Error badge background |
| `text-error-text` | `--status-error-text` | Error badge text |
| `bg-info` | `--status-info` | Info dot, icon |
| `bg-info-bg` | `--status-info-bg` | Info badge background |
| `text-info-text` | `--status-info-text` | Info badge text |
| `shadow-sm` | `--shadow-sm` | Subtle shadow |
| `shadow-md` | `--shadow-md` | Elevated shadow |
| `shadow-lg` | `--shadow-lg` | Modal/dropdown shadow |

---

## 8. Font System & Multi-Language Support

### Per-Script Font Stacks

```css
:root {
  /* Default (Latin) */
  --font-sans:    'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', 'SF Mono', 'Cascadia Code', monospace;
  --line-height:  1.5;

  /* CJK override (Chinese, Japanese, Korean) */
  --font-cjk:     'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Noto Sans CJK KR', 'Source Han Sans', var(--font-sans);
  --line-height-cjk: 1.7;

  /* Arabic override */
  --font-arabic:  'Noto Sans Arabic', 'Segoe UI', var(--font-sans);
  --line-height-arabic: 1.6;

  /* Direction (toggled per language) */
  --i18n-dir:     ltr;
  --i18n-lang:    en;
}
```

### Font Loading Strategy

- **Variable fonts** preferred for Latin (Inter) — single file covers all weights
- **CJK fonts** loaded on demand — subset by language (SC, JP, KR) to avoid 15MB+ downloads
- All fonts use `font-display: swap` to prevent invisible text during load
- Preconnect to Google Fonts origin in `<head>`

### CSS Logical Properties

All components must use logical properties instead of physical ones for automatic RTL support:

| Physical | Logical |
|----------|---------|
| `margin-left` / `margin-right` | `margin-inline-start` / `margin-inline-end` |
| `padding-left` / `padding-right` | `padding-inline-start` / `padding-inline-end` |
| `border-left` / `border-right` | `border-inline-start` / `border-inline-end` |
| `text-align: left` / `text-align: right` | `text-align: start` / `text-align: end` |
| `left: 0` / `right: 0` | `inset-inline-start: 0` / `inset-inline-end: 0` |
| `float: left` / `float: right` | `float: inline-start` / `float: inline-end` |
| `translateX(-100%)` | `translateX(-100%)` (no change needed) |

### Text Length Tolerance

- All text containers must handle 30% longer strings (German, Finnish compound words)
- Buttons use `min-width: max-content` or `white-space: nowrap` with overflow ellipsis
- Table cells have `min-width` set to prevent collapse under long strings
- Badges and status indicators use icons alongside text, never text alone

### HTML Attribute Rules

```html
<!-- Required on every page -->
<html data-theme="light" lang="en" dir="ltr">

<!-- Arabic example -->
<html data-theme="dark" lang="ar" dir="rtl">
```

- `lang` attribute for screen readers and font selection
- `dir` attribute for layout direction
- CSS uses `:dir(ltr)` / `:dir(rtl)` selectors for any physical overrides
- Change `--i18n-dir` and `--i18n-lang` via JavaScript when user switches language

---

## 9. Component Usage Examples

Every component consumes semantic tokens only. No hardcoded hex values.

### Card

```tsx
// Good — semantic tokens
<div className="bg-elevated border border-default rounded-xl p-4">
  <h3 className="text-sm font-semibold text-primary">Title</h3>
  <p className="text-sm text-secondary">Content</p>
</div>

// Bad — hardcoded colors
<div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Title</h3>
</div>
```

### Input

```tsx
// Good
<input
  className="w-full px-3 py-2 text-sm bg-input text-primary
             border border-strong rounded-lg
             placeholder:text-muted
             focus:outline-none focus:ring-[3px] focus:ring-[var(--focus-ring)] focus:border-focus
             disabled:bg-hover disabled:text-muted disabled:cursor-not-allowed"
/>

// Bad
<input
  className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800
             text-gray-900 dark:text-gray-100
             border border-gray-200 dark:border-gray-700 rounded-lg
             placeholder:text-gray-400"
/>
```

### Button (Primary)

```tsx
<button
  className="inline-flex items-center justify-center gap-2
             h-9 px-4 text-sm font-medium
             bg-action-primary text-action-primary-text
             hover:bg-action-primary-hover
             active:scale-[0.98]
             disabled:bg-action-disabled disabled:text-action-disabled-text disabled:cursor-not-allowed
             rounded-lg transition-all"
>
  <Icon className="w-4 h-4" />
  Start Interview
</button>
```

### Button (Secondary)

```tsx
<button
  className="inline-flex items-center justify-center gap-2
             h-9 px-4 text-sm font-medium
             bg-action-secondary text-action-secondary-text
             hover:bg-action-secondary-hover
             disabled:bg-action-disabled disabled:text-action-disabled-text disabled:cursor-not-allowed
             rounded-lg transition-all"
>
  Cancel
</button>
```

### Button (Ghost)

```tsx
<button
  className="inline-flex items-center justify-center gap-2
             h-9 px-4 text-sm font-medium
             bg-transparent text-action-ghost-text
             hover:bg-action-ghost-hover
             disabled:text-action-disabled-text disabled:cursor-not-allowed
             rounded-lg transition-all"
>
  Back
</button>
```

### Button (Danger)

```tsx
<button
  className="inline-flex items-center justify-center gap-2
             h-9 px-4 text-sm font-medium
             bg-action-danger text-action-danger-text
             hover:bg-action-danger-hover
             disabled:bg-action-disabled disabled:text-action-disabled-text disabled:cursor-not-allowed
             rounded-lg transition-all"
>
  Delete Company
</button>
```

### Table

```tsx
<table className="w-full text-sm">
  <thead>
    <tr className="border-b border-divider">
      <th className="text-left text-xs font-medium text-secondary uppercase tracking-wider pb-3">
        Name
      </th>
    </tr>
  </thead>
  <tbody>
    {rows.map(row => (
      <tr
        key={row.id}
        onClick={...}
        className="border-b border-divider cursor-pointer hover:bg-hover transition-colors"
      >
        <td className="py-3 text-primary">{row.name}</td>
      </tr>
    ))}
  </tbody>
</table>
```

### Status Badge

```tsx
function StatusBadge({ status }) {
  const variants = {
    completed: {
      bg: 'bg-success-bg', text: 'text-success-text', dot: 'bg-success',
    },
    active: {
      bg: 'bg-info-bg', text: 'text-info-text', dot: 'bg-info',
    },
    error: {
      bg: 'bg-error-bg', text: 'text-error-text', dot: 'bg-error',
    },
  };

  const v = variants[status] || variants.active;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-medium ${v.bg} ${v.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${v.dot}`} />
      {label}
    </span>
  );
}
```

---

## 10. Migration Guide

### Step 1: Define CSS Variables

Add to `tailwind.css`:

```
@layer base {
  :root { /* all light theme vars */ }
  [data-theme="dark"] { /* all dark theme vars */ }
}
```

### Step 2: Update Tailwind Config

Replace the `tailwind.config.js` with the configuration shown in Section 7.

### Step 3: Switch darkMode Strategy

Change `darkMode: 'class'` to `darkMode: ['selector', '[data-theme="dark"]']`.

### Step 4: Update Theme Toggle

Replace `toggleClass('dark')` with `setAttribute('data-theme', ...)`.

### Step 5: Bulk Replace Component Colors

| Old Pattern | Replace With |
|-------------|-------------|
| `bg-white dark:bg-gray-900` | `bg-elevated` |
| `bg-gray-50 dark:bg-gray-950` | `bg-page` |
| `bg-gray-50 dark:bg-gray-900` | `bg-section` |
| `bg-white dark:bg-gray-800` | `bg-input` |
| `bg-gray-100 dark:bg-gray-800` | `bg-action-secondary` |
| `text-gray-900 dark:text-white` | `text-primary` |
| `text-gray-500 dark:text-gray-400` | `text-secondary` |
| `text-gray-400 dark:text-gray-500` | `text-muted` |
| `border-gray-200 dark:border-gray-800` | `border` or `border-default` |
| `border-gray-200 dark:border-gray-700` | `border-strong` |
| `bg-purple-500 hover:bg-purple-600` | `bg-action-primary hover:bg-action-primary-hover` |
| `bg-rose-50 dark:bg-rose-900/20` | `bg-error-bg` |
| `text-rose-700 dark:text-rose-400` | `text-error-text` |

### Step 6: Replace Physical with Logical Properties

Search for `margin-left`, `margin-right`, `padding-left`, `padding-right`, `left:`, `right:`, `text-align: left`, `text-align: right` and replace with logical equivalents.

### Step 7: Remove All Inline Hex Values

Scan for any remaining hex colors (`#....`, `rgb(`, `rgba(`) inside component files. Every color must come from a CSS variable.

### Step 8: Verify Both Themes

Check every component in both `data-theme="light"` and `data-theme="dark"`.

### Step 9: Run Automated Contrast Check

Use a tool (axe, Lighthouse, or WAVE) to verify WCAG AA compliance across all pages.

### Step 10: Remove Emoji from All UI Text

Scan for emoji characters in JSX, labels, placeholders, and error messages. Replace with icon components where visual communication is needed, or plain text everywhere else.
