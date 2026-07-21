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
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'SF Mono', 'Cascadia Code', 'monospace'],
        cjk: ['Noto Sans CJK SC', 'Source Han Sans', 'sans-serif'],
        arabic: ['Noto Sans Arabic', 'sans-serif'],
      },
      colors: {
        page:      'var(--bg-page)',
        section:   'var(--bg-section)',
        elevated:  'var(--bg-elevated)',
        input:     'var(--bg-input)',
        hover:     'var(--bg-hover)',
        overlay:   'var(--bg-overlay)',

        primary:   'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        muted:     'var(--text-muted)',
        inverse:   'var(--text-inverse)',

        divider: 'var(--divider)',

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
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
      },
    },
  },
  plugins: [],
};
