// Theme tokens reconstructed from the literal hex/rgba values already
// present in the copied BondLens reference CSS (features/bondlens/bondlens.css) -
// its original tailwind.config.js was not part of the reference source
// (see docs/plans/implementation.md Task 15 Step 1). Values are not a
// Vichara brand fact; they're an inferred design-system token set for a
// portfolio demo shell.
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#f8fafc',
        surface: '#ffffff',
        zebra: '#f1f5f9',
        navy: '#1e3a8a',
        link: '#2563eb',
        gain: '#15803d',
        loss: '#dc2626',
        warn: '#b45309',
        info: '#0284c7',
        neutral: '#475569',
        'gain-tint': '#dcfce7',
        'loss-tint': '#fee2e2',
        'warn-tint': '#fef3c7',
        'info-tint': '#e0f2fe',
        'link-tint': '#dbeafe',
        'neutral-tint': '#f1f5f9',
        text: {
          hi: '#0f172a',
          md: '#475569',
          lo: '#94a3b8',
        },
        border: {
          l: '#e2e8f0',
          m: '#cbd5e1',
        },
      },
      fontSize: {
        '2xs': ['10px', { lineHeight: '14px' }],
      },
      boxShadow: {
        card: '0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.06)',
        'card-hov': '0 4px 12px rgba(15,23,42,0.08)',
      },
    },
  },
  plugins: [],
}
