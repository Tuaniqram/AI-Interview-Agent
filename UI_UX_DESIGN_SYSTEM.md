# AI Interview Agent — UI/UX Design System

> Design principles, accessibility rules, component guidelines, and experience standards for a production AI SaaS product.

---

## Table of Contents

1. [UX Principles](#1-ux-principles)
2. [Accessibility Rules](#2-accessibility-rules)
3. [Color System](#3-color-system)
4. [Typography](#4-typography)
5. [Component Rules](#5-component-rules)
   - [Card](#51-card)
   - [Input](#52-input)
   - [Button](#53-button)
   - [Table](#54-table)
   - [Form](#55-form)
   - [Status Badge](#56-status-badge)
   - [Progress Bar](#57-progress-bar)
   - [Modal / Dialog](#58-modal--dialog)
   - [Skeleton / Loading](#59-skeleton--loading)
   - [Empty State](#510-empty-state)
6. [Interview Experience Guidelines](#6-interview-experience-guidelines)
7. [Avatar Lab Guidelines](#7-avatar-lab-guidelines)
8. [Common Mistakes to Avoid](#8-common-mistakes-to-avoid)
9. [Appendix: Design References](#9-appendix-design-references)

---

## 1. UX Principles

### Principle 1: Clarity Over Creativity

Every interface element must answer four questions:

1. **What is this?** — Clear label, proper heading hierarchy, recognizable pattern
2. **Why is it here?** — Contextually grouped, purposeful placement, consistent with user goals
3. **What action can I take?** — Visible interaction states (hover, focus, cursor change, affordance)
4. **What happens next?** — Loading states, transitions, confirmation, error feedback

If an element cannot answer all four, it does not belong in the interface.

### Principle 2: Progressive Disclosure

Show users what they need when they need it.

- The Interview Room shows only: avatar, current question, input bar, status indicators
- Debug information (model type, WebSocket state, morph targets, FPS) is **never** visible to normal users
- Advanced settings are behind clear "Advanced" or "Developer" sections
- Connection status is a single colored dot — details live in a separate status panel

### Principle 3: Layered Surfaces

Content lives on distinguishable layers. Every surface elevation must be perceptibly different from its parent.

```
Page Background
    Section Surface        (different from page)
        Card Surface       (different from section)
            Input Field    (different from card)
                Hover      (different from input)
```

If two adjacent layers look the same, the hierarchy has failed.

### Principle 4: Consistency Reduces Cognitive Load

- One button style per variant (not inline random styling)
- One input style across all forms
- One card pattern across all sections
- Status colors mean the same thing everywhere (green = success/completed, red = error, yellow = warning, blue = info)

### Principle 5: Feedback Is Immediate

Every user action produces a visible state change:

| Action | Response | Timing |
|--------|----------|--------|
| Button click | Hover -> active press | < 100ms |
| Form submit | Loading state | < 300ms |
| Error | Inline message with icon | < 100ms |
| Page navigation | Skeleton or spinner | < 500ms |
| Async operation | Progress indicator | < 200ms |

### Principle 6: Accessibility Is Not Optional

There is no trade-off between accessible design and beautiful design. Every color pair passes WCAG AA. Every interactive element has visible focus. Every image and icon has a text alternative. Forms use proper label associations.

---

## 2. Accessibility Rules

### 2.1 Text Contrast

| Text Type | Minimum Ratio | Standard |
|-----------|--------------|----------|
| Normal text (< 18px / < 14px bold) | 4.5:1 | WCAG AA |
| Large text (>= 18px / >= 14px bold) | 3:1 | WCAG AA |
| Placeholder text | 4.5:1 | WCAG AA |
| Disabled text | 4.5:1 | WCAG AA |

### 2.2 Focus Visibility

- Every interactive element must have a visible focus indicator
- Focus ring: 3px solid using `--border-focus` with `--focus-ring` box-shadow
- Focus must be visible in both light and dark themes
- Use `:focus-visible` instead of `:focus` to avoid showing focus on mouse clicks
- Never use `outline: none` without providing an alternative focus style

### 2.3 Touch Targets

- Minimum touch target: 44px x 44px (WCAG 2.5.5)
- Minimum button height: 36px (with 44px for critical actions)
- Minimum input height: 36px

### 2.4 Label Association

- Every `<input>`, `<select>`, and `<textarea>` must have an associated `<label>` with `htmlFor`
- Never use placeholder text as a label replacement
- Error messages must be programmatically associated using `aria-describedby`
- Required fields must use `required` attribute plus an asterisk in the label

### 2.5 Keyboard Navigation

- All functionality must be reachable via keyboard (Tab, Enter, Escape, Arrow keys)
- Focus order must match visual order
- Tab traps are prohibited — modals must trap focus but close on Escape
- Skip-to-content link recommended for keyboard users

### 2.6 Screen Reader Support

- Icons: `aria-hidden="true"` when decorative, `aria-label` when meaningful
- Status changes: Use `aria-live="polite"` for dynamic content
- Loading: Use `aria-busy="true"` on containers during async operations
- Tables: Use `<th>` with `scope` for header cells
- Buttons: Descriptive text inside button, never just an icon without text alternative

### 2.7 Motion and Animation

- Respect `prefers-reduced-motion`: disable all non-essential animations
- Animations under 100ms do not need a reduced-motion alternative
- Transitions: Use `transition-all` sparingly — prefer specific properties (`background-color`, `border-color`, `opacity`)
- No flashing or strobing effects (WCAG 2.3.1)

### 2.8 Color Independence

- Never use color as the only means of conveying information
- Status badges: icon + text + color (not color alone)
- Score values: number + color + label (not color alone)
- Links: underline or icon in addition to color

### 2.9 Emoji Prohibition

- Never use emoji in UI text, labels, placeholders, error messages, buttons, or code comments
- Emoji rendering is inconsistent across platforms and inaccessible to screen readers
- Use the chosen icon set (Lucide or similar) for visual communication
- Use plain text for all content — format with typography tokens, not emoji

---

## 3. Color System

### 3.1 Semantic Purpose

| Token Group | Purpose |
|-------------|---------|
| Background | Establish surface hierarchy — guide the eye to content areas |
| Text | Ensure readability at every size — primary, secondary, muted |
| Border | Define boundaries without competing with content |
| Action | Communicate interactivity — hover, active, disabled |
| Status | Convey state at a glance — success, warning, error, info |

### 3.2 Score Color Mapping

| Score Range | Label | Color Token | Usage |
|-------------|-------|-------------|-------|
| 7.0 — 10.0 | Strong | `--status-success` | Green accent, filled bar, check icon |
| 5.0 — 6.9 | Developing | `--status-warning` | Amber accent, half-filled bar |
| 0.0 — 4.9 | Needs Improvement | `--status-error` | Red accent, low bar |

### 3.3 Status Color Usage

| Token | Icon/Progress Use | Background Use | Text Use |
|-------|------------------|----------------|----------|
| `--status-success` | Score dot, progress fill | Badge background | Badge label |
| `--status-warning` | Progress fill (mid) | Badge background | Badge label |
| `--status-error` | Error icon, progress fill (low) | Error message bg | Error message text |
| `--status-info` | Connection dot | Badge background | Badge label |

### 3.4 When to Use Each Text Token

| Token | Usage | Examples |
|-------|-------|----------|
| `--text-primary` | High-emphasis content | Page titles, card headings, body text, table cell values |
| `--text-secondary` | Medium-emphasis content | Labels, metadata, table headers, descriptions, subtitle text |
| `--text-muted` | Low-emphasis content | Placeholder text, disabled text, timestamps, helper text |
| `--text-inverse` | Content on brand/action surfaces | Button text, text on status badges |

---

## 4. Typography

### 4.1 Type Scale

| Level | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| Display | 24px / 1.5rem | 700 (Bold) | 1.2 | -0.02em | Page titles |
| Heading 1 | 20px / 1.25rem | 600 (Semibold) | 1.3 | -0.01em | Section titles |
| Heading 2 | 16px / 1rem | 600 (Semibold) | 1.4 | 0 | Card titles, modal titles |
| Subtitle | 14px / 0.875rem | 500 (Medium) | 1.4 | 0 | Form section headings |
| Body | 14px / 0.875rem | 400 (Regular) | 1.5 | 0 | Normal text, table cells |
| Small | 13px / 0.8125rem | 400 (Regular) | 1.4 | 0 | Metadata, field labels |
| Caption | 12px / 0.75rem | 500 (Medium) | 1.3 | 0.02em | Badges, timestamps, status labels |
| Mono | 13px / 0.8125rem | 400 (Regular) | 1.4 | 0 | Code, debug logs, URLs |

### 4.2 Font Stack

```css
/* Latin default */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Cascadia Code', monospace;

/* CJK (Chinese, Japanese, Korean) */
--font-cjk: 'Noto Sans CJK SC', 'Noto Sans CJK JP', 'Noto Sans CJK KR', 'Source Han Sans', sans-serif;
--line-height-cjk: 1.7;

/* Arabic */
--font-arabic: 'Noto Sans Arabic', 'Segoe UI', system-ui, sans-serif;
--line-height-arabic: 1.6;
```

### 4.3 Multi-Language Rules

- Line height increases for CJK scripts (1.5 -> 1.7) to accommodate taller characters
- Arabic uses a dedicated font stack for proper glyph shaping
- RTL layout is handled via CSS logical properties — never hardcode `left`/`right`
- Text containers must tolerate 30% longer strings (German, Finnish compound words)
- All strings come from an i18n system — never hardcode English text in components

### 4.4 Implementation

```css
body {
  font-family: var(--font-sans);
  line-height: var(--line-height, 1.5);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

Use Tailwind classes for all text: `text-sm`, `text-xs`, `font-medium`, `font-semibold`, `leading-relaxed`.

---

## 5. Component Rules

### 5.1 Card

#### Purpose

Group related content into a visually bounded container.

#### Anatomy

```
+-- border-default, rounded-xl, p-4/5 -----------+
|                                                 |
|  (optional header)  Title                    ← text-primary, font-semibold
|  (optional desc)    Supporting text          ← text-secondary
|                                                 |
|  Content area                                 ← text-primary / text-secondary
|                                                 |
+-------------------------------------------------+
```

#### States

| State | Background | Border | Cursor |
|-------|-----------|--------|--------|
| Default | `--bg-elevated` | `--border-default` | default |
| Hover (if clickable) | `--bg-elevated` | `--border-strong` | pointer |
| Active (if clickable) | `--bg-elevated` | `--border-strong` | pointer |

#### Rules

- Use cards sparingly — not everything needs a card. Prefer layout (gap, padding) for structural separation.
- Card title is `--text-primary` at `text-sm font-semibold`
- Card body text is `--text-secondary` at `text-sm`
- Padding: 20px default, 16px compact, 24px spacious
- Cards should never contain other cards
- Shadow is optional via `shadow-sm` — prefer border-only for a cleaner look

#### When Not to Use

- For single rows of content (use a list or table instead)
- For forms with many fields (the card border just adds visual noise)
- Inside other cards (nesting breaks the surface hierarchy)

---

### 5.2 Input

#### Purpose

Allow users to enter text, select options, or provide data.

#### Anatomy

```
+--- border-strong, rounded-lg, bg-input --------+
|  label                                       ← text-secondary, text-xs font-medium
|                                                 |
|  [  border-strong, bg-input                   ] ← placeholder: text-muted
|                                                 |
|  helper text                                  ← text-muted, text-xs
|  error text (if invalid)                      ← text-error-text, text-xs
+-------------------------------------------------+
```

#### States

| State | Border | Background | Text | Notes |
|-------|--------|-----------|------|-------|
| Default | `--border-strong` | `--bg-input` | `--text-primary` | — |
| Hover | `--border-strong` (lighten) | `--bg-input` | `--text-primary` | Cursor: text |
| Focus | `--border-focus` | `--bg-input` | `--text-primary` | + `--focus-ring` shadow |
| Filled | `--border-strong` | `--bg-input` | `--text-primary` | — |
| Error | `--status-error` | `--bg-input` | `--text-primary` | + error message below |
| Disabled | `--border-default` | `--bg-hover` (50%) | `--text-muted` | Cursor: not-allowed |

#### Rules

- Every input must have a visible `<label>` with `htmlFor`
- Placeholder is `--text-muted` — never use placeholder as label replacement
- Required fields show an asterisk in `--status-error` color
- Error messages appear below the input with error icon + text
- Helper text appears below the input with `--text-muted` color
- Input height: 36px (h-9) for text, auto for textarea
- Border radius: 8px (rounded-lg)
- Focus ring: 3px `--focus-ring` via box-shadow

#### Select

Select elements follow the same token pattern as inputs. They must include a visible chevron icon to indicate expandability.

#### Textarea

Same tokens as input. Minimum 3 rows. Resize: vertical only.

---

### 5.3 Button

#### Purpose

Trigger actions. Four variants serve different hierarchical needs.

#### Anatomy

```
+--- rounded-lg, inline-flex, items-center, gap-2, h-9 --
|                                                         |
|  [icon] Label                                       ← font-medium, text-sm
|                                                         |
+---------------------------------------------------------+
```

#### Variants

| Variant | Background | Text | Border | Hover | Active | Disabled |
|---------|-----------|------|--------|-------|--------|----------|
| Primary | `--action-primary` | `--action-primary-text` | None | `--action-primary-hover` | scale(0.98) | `--action-disabled` bg + text |
| Secondary | `--action-secondary` | `--action-secondary-text` | None (or `--border-default`) | `--action-secondary-hover` | scale(0.98) | `--action-disabled` bg + text |
| Ghost | transparent | `--action-ghost-text` | None | `--action-ghost-hover` | scale(0.98) | `--action-disabled-text` |
| Danger | `--action-danger` | `--action-danger-text` | None | `--action-danger-hover` | scale(0.98) | `--action-disabled` bg + text |

#### Sizes

| Size | Height | Padding Horizontal | Font |
|------|--------|-------------------|------|
| sm | 32px (h-8) | 12px (px-3) | 13px (text-xs) |
| md (default) | 36px (h-9) | 16px (px-4) | 14px (text-sm) |
| lg | 44px (h-11) | 20px (px-5) | 14px (text-sm) |

#### Rules

- Buttons use flat colors — never gradients
- Icon inside button is `w-4 h-4` for md/lg, `w-3.5 h-3.5` for sm
- Text and icon share the same color token
- Loading state: replace icon with spinner, disable interaction
- Disabled state: use dedicated tokens, never just `opacity-50`
- Grouped buttons: use `gap-3` between them

#### When To Use Each Variant

| Action Type | Variant | Example |
|-------------|---------|---------|
| Primary call to action | Primary | Start Interview, Save, Create Company |
| Secondary action | Secondary | Cancel, Back, Discard |
| Subtle action | Ghost | Edit, View Details, Filter |
| Destructive action | Danger | Delete Company, Remove Document |

---

### 5.4 Table

#### Purpose

Display structured data in rows for quick scanning and comparison.

#### Anatomy

```
+-------------------------------------------------------+
|  Header 1    Header 2    Header 3    Header 4         |  ← text-secondary, text-xs, uppercase
+-------------------------------------------------------+
|  Cell 1      Cell 2      Cell 3      Cell 4           |  ← border-divider separator
|  Cell 1      Cell 2      Cell 3      Cell 4           |  ← hover: bg-hover
+-------------------------------------------------------+
```

#### Rules

- Header text: `--text-secondary`, 12px (text-xs), 600 weight, uppercase, `tracking-wider`
- Body text: `--text-primary`, 14px (text-sm), 400 weight
- Row separator: `--divider` border-bottom
- Row hover: `--bg-hover` at 50% opacity — subtle enough not to overwhelm
- Clickable rows: pointer cursor on the entire row, no text decoration
- Cell padding: 12px vertical, 16px horizontal
- Tables fill parent width — no fixed width unless necessary
- Tables are **not** wrapped in Cards — they use the parent container's background

#### Column Alignment

| Data Type | Alignment |
|-----------|-----------|
| Text (names, descriptions) | `text-align: start` |
| Numbers (scores, counts) | `text-align: end` (right in LTR) |
| Status badges | `text-align: center` |
| Actions (buttons, icons) | `text-align: end` |

#### Empty State

When a table has no data, show a centered `EmptyState` component with icon, message, and optional CTA — not a table with "No data" in a single row.

---

### 5.5 Form

#### Purpose

Collect structured data from users with clear guidance and validation.

#### Anatomy

```
+------------------------------------------------------------+
|  Form Section Title                                      ← subtitle
|                                                             |
|  Field Group Label                                       ← text-secondary, 13px/500
|  +--------------------------------------------------------+ |
|  | Field 1 label *   [ input                        ]     | |
|  |                   (helper text)                        | |
|  | Field 2 label     [ input                        ]     | |
|  |                   (optional helper text)               | |
|  +--------------------------------------------------------+ |
|                                                             |
|  [ Cancel ]  [ Submit ]                                   |
+------------------------------------------------------------+
```

#### Spacing

| Element | Spacing |
|---------|---------|
| Between field groups | 24px |
| Between fields within group | 20px |
| Between label and input | 6px |
| Between input and helper/error | 4px |
| Between form and buttons | 24px |

#### Rules

- Group related fields together with a group label
- Label: `--text-secondary`, 13px (text-sm), 500 weight
- Required fields: asterisk in `--status-error` after label
- Helper text: `--text-muted`, 12px (text-xs), below input
- Error text: `--status-error-text`, 12px (text-xs), with error icon, below input
- Use `<fieldset>` for radio/checkbox groups
- Submit button is `--action-primary`, cancel is `--action-ghost-text`

#### Validation

- Validate on blur (not on every keystroke, not only on submit)
- Show all field errors on submit attempt
- Inline errors below the specific field, not a generic banner
- Success state: brief inline confirmation or auto-dismiss banner

---

### 5.6 Status Badge

#### Purpose

Communicate the state of an entity at a glance.

#### Anatomy

```
+--- rounded-full, px-2.5, py-0.5, gap-1.5 ---------+
|                                                     |
|  (●) Label                                       ← Caption font weight
|                                                     |
+-----------------------------------------------------+
```

#### Rules

- Always use a colored dot + text — never color alone
- Three color sources consumed: `dot`, `bg`, `text` per status
- Badge text: `--status-*-text`, 12px (text-xs), 500 weight
- Badge background: `--status-*-bg`
- Dot: `--status-*` (the saturated version)
- Badges are inline elements — do not use block display
- Border radius: `rounded-full` (pill shape)

#### Status Mapping

| Internal Status | Display Label | Dot | Background | Text |
|----------------|---------------|-----|------------|------|
| completed | Completed | `--status-success` | `--status-success-bg` | `--status-success-text` |
| active | Active | `--status-info` | `--status-info-bg` | `--status-info-text` |
| in_progress | In Progress | `--status-warning` | `--status-warning-bg` | `--status-warning-text` |
| error | Error | `--status-error` | `--status-error-bg` | `--status-error-text` |
| initiated | Initiated | `--text-muted` | `--bg-hover` | `--text-muted` |
| uploaded | Uploaded | `--status-success` | `--status-success-bg` | `--status-success-text` |
| processed | Processed | `--status-info` | `--status-info-bg` | `--status-info-text` |

---

### 5.7 Progress Bar

#### Purpose

Show completion progress for interviews, uploads, or multi-step processes.

#### Anatomy

```
+---------------------------------------------------+
|  Track: rounded-full, bg-elevated                   |
|  [████████████░░░░░░░░░░░░░░░░░░░░░]  ← filled:   |
|    --status-success / --status-warning              |
|  Question 3 of 10                                   |
+---------------------------------------------------+
```

#### Rules

- Track background: `--bg-elevated` (the layer below the card or parent)
- Fill color: `--status-success` (high), `--status-warning` (mid), `--status-error` (low)
- Fill is flat color — never gradient
- Label below the bar: left = description (text-secondary), right = count (text-primary)
- Animation: `transition-all duration-500 ease-out` for smooth width change
- Always show numeric context (current/total or percentage)

---

### 5.8 Modal / Dialog

#### Purpose

Present focused content or confirm actions without navigating away.

#### Anatomy

```
+---------------------------------------------------------+
|  (overlay: --bg-overlay, fixed, z-50)                    |
|                                                          |
|  +-- bg-elevated, shadow-lg, rounded-xl, max-w-sm ----+ |
|  |                                                     | |
|  |  [icon]  Title                              [close] | |
|  |                                                     | |
|  |  Message / content                                  | |
|  |                                                     | |
|  |           [Cancel]    [Confirm]                     | |
|  +-----------------------------------------------------+ |
+---------------------------------------------------------+
```

#### Rules

- Overlay background: `--bg-overlay`
- Dialog background: `--bg-elevated` with `shadow-lg`
- Close button in top-right corner — ghost variant
- Focus trap: Tab cycles within dialog, Escape to close
- Title: `--text-primary`, text-sm, font-semibold
- Body: `--text-secondary`, text-sm
- Actions: align to end (start in RTL), danger on left, confirm on right
- Two variants: `default` (primary confirm) and `danger` (danger confirm)
- Clicking overlay dismisses the dialog

---

### 5.9 Skeleton / Loading

#### Purpose

Indicate content is loading without abrupt layout shifts.

#### Anatomy

```
+---------------------------------------------------+
|  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░    ← animate-pulse      |
|  ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░                          |
|  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                          |
|                                                     |
|  Background: --bg-elevated (skeleton color)         |
|  Animation: animate-pulse (opacity 1 -> 0.5 -> 1)   |
+---------------------------------------------------+
```

#### Rules

- Skeleton background: `--bg-elevated` with `animate-pulse`
- Shape variants: text (h-4, rounded), circle (rounded-full), rect (rounded-lg)
- Skeletons match the dimensions of the content they replace
- Never show skeletons for content that loaded in under 300ms
- Use `aria-busy="true"` on containers during loading

---

### 5.10 Empty State

#### Purpose

Guide users when no content exists, with a clear next action.

#### Anatomy

```
+---------------------------------------------------+
|                                                     |
|               [icon]                             ← text-muted (icon color)
|           No sessions yet                        ← text-primary, font-medium
|     Start your first interview to see            ← text-secondary
|             results here.                        ← text-secondary
|                  [button]                        ← action-primary
|                                                     |
+---------------------------------------------------+
```

#### Rules

- Icon: 32px, `--text-secondary` or `--text-muted`
- Title: `--text-primary`, text-base, font-medium
- Description: `--text-secondary`, text-sm, max-width 300px, centered
- Action CTA: primary button variant
- Centered layout with 64px padding top/bottom
- Do not show empty state inside a card — use the full container width

---

## 6. Interview Experience Guidelines

### 6.1 Information Priority

The interview screen has a strict visual priority system. Every element is assigned a layer.

```
Layer 1 (always, full screen) → AI Avatar (primary focus)
Layer 2 (always, bottom)     → Current question overlay (semi-transparent)
Layer 3 (always, bottom bar) → Input bar: mic, text field, send button
Layer 4 (contextual)          → Speaking/listening indicators
Layer 5 (top bar, minimal)   → Back button, timer, progress, connection dot
Layer 6 (admin only)          → Debug info — NEVER visible to normal users
```

### 6.2 Layout

```

  ┌─────────────────────────────────────────────────────┐
  │                                                      │
  │  [< Back]              [3:45]              [3/10] ● │  ← Layer 5 (absolute top)
  │                                                      │
  │                                                      │
  │                    ┌──────────┐                      │
  │                    │          │     ┌──────┐         │
  │                    │  AVATAR  │     │CAMERA│         │  ← Layer 1
  │                    │          │     │      │         │
  │                    └──────────┘     └──────┘         │
  │                                                      │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐    │  ← Layer 2 (absolute bottom)
  │  │  Q3: Tell me about your experience with...    │    │
  │  │  [Technical  ●]  Speaking...  ●               │    │  ← Layer 4
  │  └──────────────────────────────────────────────┘    │
  │                                                      │
  │  ┌──────────────────────────────────────────────┐    │  ← Layer 3 (fixed bottom bar)
  │  │  [Mic]  [ Type your answer...       ] [Send] │    │
  │  └──────────────────────────────────────────────┘    │
  └─────────────────────────────────────────────────────┘
```

### 6.3 Components

#### Avatar Area (Layer 1)

- Takes 60%+ of screen real estate
- Never covered by panels or overlays
- Camera preview is a small (160x120) rounded rectangle in top-right corner
- Camera is toggleable — off by default

#### Question Overlay (Layer 2)

- Semi-transparent background: `--bg-elevated` at 90% opacity with `backdrop-blur-sm`
- Question number badge: `--action-primary` background, `--action-primary-text`, pill shape
- Question text: `--text-primary`, 15px, leading-relaxed
- Phase badge (Technical, Behavioral, etc.): `--action-secondary` background, `--text-secondary` text
- Fade-in transition when question changes

#### Input Bar (Layer 3)

- Fixed at bottom, full width
- Background: `--bg-page` with top border `--border-default`
- Mic button: 44px circle, `--action-secondary` when off, `--status-error` (red) with pulse when recording
- Text input: same tokens as standard input, rounded-xl
- Send button: 44px circle, `--action-primary`, disabled when empty
- Icon sizes: `w-5 h-5` for mic and send

#### Status Indicators (Layer 4)

- Horizontal row below the question overlay
- Speaking dot: `--status-success` with pulse animation
- Listening dot: `--status-info` with pulse animation
- Connection dot (top-right corner of screen): `--status-success` (connected), `--status-warning` (connecting), `--status-error` (disconnected)
- Text: `--text-muted`, 11px (text-xs), with icon

#### Top Bar (Layer 5)

- Back button: ghost variant, small
- Timer: `--text-secondary`, 13px (text-sm), monospace
- Progress: "3/10" format, `--text-primary`, 13px (text-sm)
- Connection dot: 8px circle in top-right corner

### 6.4 Evaluation Screen

When the AI evaluates an answer, the evaluation appears as a **slide-up panel** — not a sudden overlay.

- Panel slides up from the bottom, replacing the question overlay
- Background: `--bg-elevated` with `backdrop-blur-md`
- Score badge: large, with color coding (green/amber/red)
- Evaluation text: `--text-secondary`, 14px, readable paragraph
- Auto-dismiss after configurable delay, or user taps to continue
- Transition: 300ms ease-out slide-up

### 6.5 States

| State | Avatar | Question Area | Input Bar | Status |
|-------|--------|--------------|-----------|--------|
| Avatar speaking | Speaking animation (lip sync + gesture) | Shows question | Mic enabled, send disabled | Speaking dot visible |
| User listening | Listening posture (slight lean, eyebrow raise) | Shows question | Mic recording (red pulse) | Listening dot visible |
| User typing | Idle posture, neutral expression | Shows question | Mic off, text input active | — |
| AI thinking | Thinking posture (head tilt, hand to chin) | "Analyzing your answer..." | All disabled | Thinking text |
| Error | — | Error message | All disabled | Error dot, reconnection message |
| Disconnected | Static pose | "Connection lost" | All disabled | Red dot |

### 6.6 Eliminated Elements

The following items are **never** visible in the production interview screen:

- Model type badge ("3D Model" / "Procedural")
- Debug viseme/morph target values
- WebSocket connection details
- FPS or latency metrics
- Audio waveform visualization
- Browser speech support warnings (handle gracefully instead)

All of these belong in the Avatar Lab.

---

## 7. Avatar Lab Guidelines

### 7.1 Purpose

The Avatar Lab is a **developer tool** for testing and debugging the 3D avatar. It has a different audience and a different visual language from the user-facing interview.

### 7.2 Audience

- Developers working on animation, lip sync, and gesture systems
- QA testers verifying avatar behavior
- Product managers evaluating animation quality

### 7.3 Visual Language

- Uses the same `[data-theme="dark"]` theme as the rest of the app
- Densest layout in the system — maximize information per pixel
- Labels are developer-oriented: clear naming, no marketing polish
- Debug information uses monospace font in readable panels

### 7.4 Layout

```

  ┌──────────────────────────────────────────────────┐
  │                                                    │
  │              ┌──────────────────────┐              │
  │              │                      │  ┌───────────┤
  │              │                      │  │ Controls  │
  │              │    AVATAR PREVIEW    │  │ ─────     │
  │              │                      │  │ Body:     │
  │              │                      │  │ idle      │
  │              │                      │  │ speaking  │
  │              │                      │  │ listening │
  │              │                      │  │           │
  │              │                      │  │ Emotion:  │
  │              └──────────────────────┘  │ neutral   │
  │                                        │ excited   │
  │                                        │           │
  │                                        │ [Speak]   │
  │                                        │           │
  │                                        ├───────────┤
  │                                        │ Status    │
  │                                        │ WS: ●     │
  │                                        │ Spk: ●    │
  │                                        ├───────────┤
  │                                        │ Debug     │
  │                                        │ [toggle]  │
  │                                        │ pre {}    │
  └──────────────────────────────────────────────────┘
```

### 7.5 Panel Specifications

#### Avatar Preview

- Full-height, left/center — same renderer as the interview room
- No overlays on the avatar itself
- Background: `--bg-page`

#### Controls Panel (Right Sidebar)

- Width: 320px
- Background: `--bg-section` with left border `--border-default`
- Scrollable content
- Sections separated by 20px gaps with header labels
- Controls are dense: small buttons, compact grids, close spacing

#### Tab Structure (Optional, for larger screens)

| Tab | Content |
|-----|---------|
| Controls | Body state, emotion, gesture triggers, speak text |
| State | Morph target values, bone rotations, animation layer weights |
| Logs | Timestamped, filterable event log (monospace, line-numbered) |

#### Debug Section

- Collapsible by default — hidden behind a checkbox or toggle
- When expanded: monospace pre block with full animation state
- Background: `--bg-input` or `--bg-elevated` with monospace font
- Content: gesture name, state, progress, phase, elapsed time, bone rotations
- Connection status: WebSocket connected/disconnected with dot indicator
- Speaking status: currently speaking with audio time

### 7.6 Control Specifications

| Control | Type | Layout |
|---------|------|--------|
| Body state | Radio button group | 2x2 grid, compact buttons |
| Emotion | Button group | 3x2 grid, compact buttons |
| Gesture trigger | Button group | 2-column scrollable grid |
| Speak text | Textarea (3 rows) + button | Stacked |
| Stop gesture | Button | Full width, danger variant |
| Debug toggle | Checkbox + label | Inline with section header |

### 7.7 When to Add to Avatar Lab

Add new UI here when:
- You need to test a new animation, gesture, or expression
- You need to debug lip-sync timing or morph target issues
- You want to verify avatar state machine transitions
- You need to test WebSocket audio streaming

---

## 8. Common Mistakes to Avoid

| # | Mistake | Why It Fails | Correct Approach |
|---|---------|-------------|------------------|
| 1 | Pure black background (#000) | Creates eye strain, hides depth perception | Use `--bg-page` (#0a0a0b) — a very dark gray preserves depth |
| 2 | White cards on white page with invisible inputs | Inputs disappear — users cannot find where to type | Differentiate with `--bg-input` + `--border-strong` on a card with `--border-default` |
| 3 | Placeholder as label replacement | Accessibility failure — disappears on input, no association | Always use `<label htmlFor="...">` + placeholder is supplementary |
| 4 | Gray text on dark gray background | WCAG contrast failure (2.9:1, needs 4.5:1) | Use `--text-secondary` which is verified to pass on every surface |
| 5 | Inconsistent button heights | Visual noise, lack of rhythm | Define 3 sizes (sm/md/lg) and use them consistently across the app |
| 6 | Debug information in production UI | Confuses users, makes product feel unfinished | All debug goes in Avatar Lab with a toggle — never in Interview Room |
| 7 | Gradient backgrounds on buttons | Look dated, inconsistent with flat design language | Flat colors with clean hover transition |
| 8 | Overusing cards for everything | Everything looks the same — no visual hierarchy | Use layout (gap, padding, section backgrounds) for structure, cards only for grouped content |
| 9 | Missing focus states on interactive elements | Keyboard users cannot navigate | Every button, input, link, and clickable element must have visible `:focus-visible` |
| 10 | Single accent color for everything | No semantic meaning — errors, warnings, and info all look the same | Use the full status palette: success (green), warning (amber), error (red), info (blue) |
| 11 | 100% width inputs in every context | Forms feel stretched, hard to scan | Use `max-w-sm` for short fields, `max-w-md` for standard fields. Full width only for textarea |
| 12 | Using emoji in UI | Inconsistent rendering across platforms, inaccessible to screen readers | Use Lucide icons for visual communication, plain text for labels |
| 13 | Hover-only interactions | Touch users and keyboard users never see hover-only content | All actions must be reachable without hover — show on focus or tap as well |
| 14 | Layout that only works in English | Broken in RTL languages or with long translated strings | Use CSS logical properties, test with 30% longer text, support `dir` attribute |
| 15 | Animations without reduced-motion support | Causes discomfort for users with vestibular disorders | Wrap all animations in `@media (prefers-reduced-motion: no-preference)` |

---

## 9. Appendix: Design References

### Visual Direction

The design language follows these product aesthetics:

| Product | Characteristics to Emulate |
|---------|---------------------------|
| Linear | Clean surfaces, excellent typography, subtle borders, clear interaction states |
| Vercel | Strong contrast hierarchy, minimal decoration, purpose-driven color |
| Stripe | Professional blue-purple accent, generous whitespace, readable forms |
| OpenAI / ChatGPT | Clean dark theme, focus on content, avatar-centric interaction |

### What to Avoid

- Gaming UI aesthetics (glowing elements, heavy gradients, futuristic borders)
- Neon colors on dark backgrounds
- Excessive glassmorphism or frosted-glass effects
- Skeuomorphic 3D button styles
- Animated backgrounds or particle effects

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-20 | Design System | Initial release |
