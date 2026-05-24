/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      fontFamily: {
        poppins: ['Poppins', 'sans-serif'],
        'zen-maru': ['"Zen Maru Gothic"', 'sans-serif'],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        success: { DEFAULT: 'hsl(var(--success))', foreground: 'hsl(var(--success-foreground))' },
        theme: {
          light: 'hsl(var(--theme-light))',
          medium: 'hsl(var(--theme-medium))',
          dark: 'hsl(var(--theme-dark))',
        },
      },
      borderRadius: { lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)' },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(124,58,237,0)' },
          '50%': { boxShadow: '0 0 22px 4px rgba(124,58,237,.35)' },
        },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        'slide-up': { from: { opacity: 0, transform: 'translateY(6px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        shimmer: 'shimmer 1.6s linear infinite',
        'slide-up': 'slide-up .25s ease-out',
      },
    },
  },
  plugins: [],
}
