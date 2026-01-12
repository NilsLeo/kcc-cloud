/**
 * Sentry Client Configuration
 * Captures console.warn() and console.error() from the browser
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Adjust this value in production, or use tracesSampler for greater control
  tracesSampleRate: 0.1, // 10% of transactions for performance monitoring

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Capture console.warn and console.error as Sentry events
  integrations: [
    Sentry.captureConsoleIntegration({
      levels: ["warn", "error"], // Only capture warnings and errors
    }),
    Sentry.breadcrumbsIntegration({
      console: true, // Capture all console logs as breadcrumbs (context)
      dom: true,
      fetch: true,
      history: true,
      xhr: true,
    }),
  ],

  // Session Replay - captures user interactions for debugging
  replaysOnErrorSampleRate: 1.0, // 100% of errors get session replays
  replaysSessionSampleRate: 0.1, // 10% of normal sessions get replays

  // Filter out sensitive data
  beforeSend(event) {
    // Don't send events if no DSN is configured
    if (!process.env.NEXT_PUBLIC_SENTRY_DSN) {
      return null;
    }

    // Filter out specific errors if needed
    // Example: if (event.message?.includes('specific error')) return null;

    return event;
  },

  // Enrich events with additional context
  beforeBreadcrumb(breadcrumb) {
    // Filter sensitive breadcrumbs if needed
    if (breadcrumb.category === 'console' && breadcrumb.level === 'log') {
      // Keep console.log as breadcrumbs but don't make them overly verbose
      return breadcrumb;
    }
    return breadcrumb;
  },

  // Set environment
  environment: process.env.NODE_ENV || 'development',
});
