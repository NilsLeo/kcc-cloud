"use client"

import { useEffect } from "react"
import { log, logError, logWarn, logDebug } from "@/lib/logger"

/**
 * Global error handler component that suppresses expected errors from appearing in console
 * Specifically handles "Upload cancelled by user" errors which are expected user actions
 */
export function ErrorBoundary({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Handle unhandled promise rejections
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      // Suppress "Upload cancelled by user" errors - these are expected
      if (event.reason?.message?.includes("cancelled by user") || event.reason?.message?.includes("Upload cancelled")) {
        event.preventDefault() // Prevents console error
        log("[ErrorBoundary] Suppressed expected cancellation error")
        return
      }

      // Let all other errors through to console
    }

    window.addEventListener("unhandledrejection", handleUnhandledRejection)

    return () => {
      window.removeEventListener("unhandledrejection", handleUnhandledRejection)
    }
  }, [])

  return <>{children}</>
}
