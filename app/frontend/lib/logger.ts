interface LogContext {
  [key: string]: any
}

class MangaConverterLogger {
  private apiBaseUrl: string
  private logThrottle: Map<string, number> = new Map()
  private throttleWindowMs = 5000 // 5 seconds throttle window

  constructor() {
    this.apiBaseUrl =
      process.env.NODE_ENV === "production" ? process.env.NEXT_PUBLIC_API_URL || "" : "http://localhost:8060"
  }

  private shouldThrottleLog(message: string): boolean {
    const now = Date.now()
    const lastLogged = this.logThrottle.get(message)

    if (!lastLogged || now - lastLogged > this.throttleWindowMs) {
      this.logThrottle.set(message, now)
      return false
    }
    return true
  }

  private async sendLog(
    level: "info" | "error" | "warning" | "debug",
    message: string,
    jobId?: string,
    context?: LogContext,
  ) {
    // Skip debug and info logs in production, always allow error/warning
    if (process.env.NODE_ENV === "production" && (level === "debug" || level === "info")) {
      // Only allow critical info logs (errors, warnings, conversion events)
      if (!message.includes("Conversion event:") && !message.includes("error") && !message.includes("failed")) {
        return
      }
    }

    // Throttle repetitive logs (except errors)
    if (level !== "error" && this.shouldThrottleLog(message)) {
      return
    }
    // Server-side: send directly to backend API
    if (typeof window === "undefined") {
      try {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://backend:8060"
        const logData = {
          level,
          message,
          job_id: jobId,
          user_id: null, // No user_id on server-side
          context: {
            timestamp: new Date().toISOString(),
            source: "frontend-server",
            ...context,
          },
        }

        await fetch(`${backendUrl}/api/log`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(logData),
        })
      } catch (error) {
        // Fallback to console logging if backend is unreachable
        console.log(`[SERVER-SIDE ${level.toUpperCase()}] ${message}`, { jobId, context })
      }
      return
    }

    // Client-side: send to frontend API route which forwards to backend
    try {
      const logData = {
        level,
        message,
        job_id: jobId,
        user_id: this.getUserId(),
        context: {
          timestamp: new Date().toISOString(),
          user_agent: navigator.userAgent,
          url: window.location.href,
          ...context,
        },
      }

      await fetch("/api/log", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(logData),
      })
    } catch (error) {
      console.error("Failed to log to backend:", error)
      // Fallback to console logging
      console.log(`[${level.toUpperCase()}] ${message}`, { jobId, context })
    }
  }

  private getUserId(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("session_key")
    }
    return null
  }

  async info(message: string, jobId?: string, context?: LogContext) {
    await this.sendLog("info", message, jobId, context)
  }

  async error(message: string, jobId?: string, context?: LogContext) {
    await this.sendLog("error", message, jobId, context)
  }

  async warning(message: string, jobId?: string, context?: LogContext) {
    await this.sendLog("warning", message, jobId, context)
  }

  async debug(message: string, jobId?: string, context?: LogContext) {
    await this.sendLog("debug", message, jobId, context)
  }

  // Convenience method for conversion events
  async logConversionEvent(
    event: "upload_started" | "upload_completed" | "conversion_started" | "conversion_completed" | "download_started",
    jobId: string,
    context?: LogContext,
  ) {
    await this.info(`Conversion event: ${event}`, jobId, {
      event_type: event,
      ...context,
    })
  }

  // Log errors with stack traces
  async logError(error: Error, jobId?: string, context?: LogContext) {
    await this.error(error.message, jobId, {
      error_name: error.name,
      error_stack: error.stack,
      ...context,
    })
  }

  // Log performance metrics
  async logPerformance(action: string, duration: number, jobId?: string, context?: LogContext) {
    await this.info(`Performance: ${action}`, jobId, {
      action,
      duration_ms: duration,
      ...context,
    })
  }

  // Console-only logging methods (no backend forwarding)
  // These are simple replacements for console.log with timestamps

  private shouldSuppressConsole(message: string): boolean {
    // Allow explicit override to keep verbose logs
    if (process.env.NEXT_PUBLIC_VERBOSE_LOGS === 'true') return false

    // Noisy prefixes we don't want in consoles
    const noisyPrefixes = [
      '[UI] ETA tick',
      '[UI] Reading File progress (ticker)',
      '[UI] Reading File ETA tick',
      '[UI] Converting progress (ticker)',
      '[UI] Upload ETA tick',
      '[UI] Uploading progress:',
      '[useSession]',
      '[MULTIPART]',
      '[MULTIPART UPLOAD]',
      '[TIMING]',
      '[STATUS CHANGE]',
      '[WEBSOCKET]',
      '[WebSocket]',
      '[HomePage]',
      'Job creation successful',
      'Job created -',
      'Job ID callback',
      'Job ID received successfully',
      '=== UPLOAD FLOW',
      'Deferring per-job subscription',
      'Starting multipart upload',
      'Waiting for job ID',
      'POST /jobs response',
      'Sending POST request to /api/jobs',
    ]

    return noisyPrefixes.some((p) => message.startsWith(p))
  }

  log(message: string, ...args: any[]) {
    if (this.shouldSuppressConsole(message)) return
    const timestamp = new Date().toISOString()
    console.log(`[${timestamp}] ${message}`, ...args)
  }

  logError(message: string, ...args: any[]) {
    const timestamp = new Date().toISOString()
    console.error(`[${timestamp}] ${message}`, ...args)
  }

  logWarn(message: string, ...args: any[]) {
    const timestamp = new Date().toISOString()
    console.warn(`[${timestamp}] ${message}`, ...args)
  }

  logDebug(message: string, ...args: any[]) {
    if (this.shouldSuppressConsole(message)) return
    const timestamp = new Date().toISOString()
    console.debug(`[${timestamp}] ${message}`, ...args)
  }
}

// Create singleton instance
export const logger = new MangaConverterLogger()

// Convenience exports for console-only logging
export const log = logger.log.bind(logger)
export const logError = logger.logError.bind(logger)
export const logWarn = logger.logWarn.bind(logger)
export const logDebug = logger.logDebug.bind(logger)

// Legacy function for backwards compatibility
export async function logToBackend(
  level: "info" | "error" | "warning",
  message: string,
  jobId?: string,
  context?: Record<string, any>,
) {
  await logger[level](message, jobId, context)
}
