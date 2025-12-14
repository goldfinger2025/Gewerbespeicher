/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  // Safelist for dynamically generated classes that Tailwind can't detect
  safelist: [
    // Status colors (bg)
    'bg-slate-100', 'bg-slate-200',
    'bg-blue-100', 'bg-blue-50', 'bg-blue-50/50',
    'bg-emerald-100', 'bg-emerald-50', 'bg-emerald-50/50',
    'bg-amber-100', 'bg-amber-50',
    'bg-green-100',
    'bg-red-100',
    'bg-purple-100', 'bg-purple-50', 'bg-purple-50/50',
    // Status colors (text)
    'text-slate-600', 'text-slate-700',
    'text-blue-600', 'text-blue-700',
    'text-emerald-600', 'text-emerald-700',
    'text-amber-600', 'text-amber-700',
    'text-green-600', 'text-green-700',
    'text-red-600', 'text-red-700',
    'text-purple-600', 'text-purple-700',
    // Border colors for scenarios
    'border-blue-300', 'border-emerald-300', 'border-purple-300',
  ],
  theme: {
    extend: {
      colors: {
        // Brand Colors
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        // Solar/Energy themed
        solar: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        // Battery/Storage themed
        battery: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
