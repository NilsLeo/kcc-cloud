/**
 * Sentry Server Configuration
 * Captures errors from Next.js server-side (API routes, SSR)
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Adjust this value in production, or use tracesSampler for greater control
  tracesSampleRate: 0.1,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Capture console.warn and console.error on server-side too
  integrations: [
    Sentry.captureConsoleIntegration({
      levels: ["warn", "error"],
    }),
  ],

  // Filter out sensitive data
  beforeSend(event) {
    // Don't send events if no DSN is configured
    if (!process.env.NEXT_PUBLIC_SENTRY_DSN) {
      return null;
    }

    return event;
  },

  // Set environment
  environment: process.env.NODE_ENV || 'development',
});
