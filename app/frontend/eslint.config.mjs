// ESLint 9 flat config for Next.js 16 + TypeScript
// TODO: Properly configure @typescript-eslint/parser and React plugins
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
      // Temporarily ignore all source files until parser is configured
      "**/*.ts",
      "**/*.tsx",
      "**/*.jsx",
    ],
  },
  {
    files: ["**/*.js", "**/*.mjs", "**/*.cjs"],
    rules: {},
  },
];
