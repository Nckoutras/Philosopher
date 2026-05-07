/** @type {import('tailwindcss').Config} */
module.exports = {
  // Light mode only per DESIGN_SYSTEM_v4 §1.1.
  // 'class' kept for backwards compat with components that may still
  // reference dark: utilities; light is force-locked in layout.tsx.
  darkMode: 'class',
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      // Spec colors per DESIGN_SYSTEM_v4 §1.2 (11 tokens).
      colors: {
        vellum: '#FAF4E6',
        paper: '#FFFFFF',
        linen: {
          DEFAULT: '#E8DCC4',
          deep: '#DDD0B5',
        },
        edge: '#D4C8B0',
        ink: '#1F1B14',
        charcoal: '#5A5246',
        sepia: '#8A7E6A',
        bronze: {
          DEFAULT: '#A8884A',
          dark: '#8A7340',
        },
        rust: '#A05A3C',
        gold: '#A8884A',
      },
      borderWidth: {
        0.5: '0.5px',
      },
      borderRadius: {
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
      fontFamily: {
        cormorant: ['var(--font-cormorant)', 'Georgia', 'serif'],
        lora: ['var(--font-lora)', 'Georgia', 'serif'],
        sans: ['var(--font-lora)', 'Georgia', 'serif'],
        serif: ['var(--font-lora)', 'Georgia', 'serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 1.4s linear infinite',
      },
    },
  },
  plugins: [],
}
