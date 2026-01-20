// Minimal ESLint configuration for Next.js 16 + ESLint 9
// TODO: Add proper TypeScript linting rules and React rules
export default [
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "out/**",
      "public/**",
      "dist/**",
      "build/**",
      "*.config.js",
      "*.config.mjs",
      "*.config.ts",
      "*.tsbuildinfo",
    ],
  },
  {
    files: ["**/*.{js,mjs,cjs,jsx,ts,tsx}"],
    rules: {
      // Minimal rules - just to get linting working
      // Most rules disabled until proper TS/React ESLint plugins are configured
    },
  },
];
