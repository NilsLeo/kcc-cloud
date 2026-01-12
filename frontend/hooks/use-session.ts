"use client"

/**
 * React hook for session management
 * Supports both automatic and lazy initialization
 */

import { useCallback, useEffect, useState } from "react"
import { ensureSession, getSessionKey } from "@/lib/session"
import { useUser, useAuth } from "@clerk/nextjs"

const isClerkConfigured = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

interface UseSessionOptions {
  /**
   * If true, initializes session immediately on mount
   * If false, session is only initialized when initializeSession() is called
   * Default: false (lazy initialization)
   */
  autoInitialize?: boolean
}

export function useSession(options: UseSessionOptions = {}) {
  const { autoInitialize = false } = options
  const IS_DEV = process.env.NODE_ENV !== "production"
  const [sessionKey, setSessionKey] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [hasInitialized, setHasInitialized] = useState(false)

  // Use Clerk's hooks to get real authentication state
  const { isSignedIn, user } = useUser()
  const { getToken } = useAuth()

  const initializeSession = useCallback(async () => {
    // Don't re-initialize if already done
    if (hasInitialized) {
      if (IS_DEV) console.log("[useSession] Already initialized, skipping")
      return sessionKey
    }

    try {
      setIsLoading(true)
      setError(null)

      let clerkToken: string | undefined

      // Get Clerk token if user is signed in
      if (isSignedIn && getToken) {
        clerkToken = (await getToken()) || undefined
        if (IS_DEV) console.log("[useSession] Got Clerk token for authenticated user")
      }

      if (IS_DEV) console.log("[useSession] Initializing session", {
        isClerkConfigured,
        isSignedIn,
        hasToken: !!clerkToken,
      })

      // Ensure session exists (creates or claims as needed)
      const session = await ensureSession(
        clerkToken,
        user?.primaryEmailAddress?.emailAddress,
        user?.firstName || undefined,
        user?.lastName || undefined
      )
      if (IS_DEV) console.log("[useSession] Session initialized successfully", { session })
      setSessionKey(session)
      setHasInitialized(true)
      return session
    } catch (err) {
      console.error("[useSession] Failed to initialize session:", err)
      setError(err instanceof Error ? err : new Error("Unknown error"))

      // Fallback: try to use existing session from localStorage
      const existingSession = getSessionKey()
      if (existingSession) {
        if (IS_DEV) console.log("[useSession] Using fallback session from localStorage", { existingSession })
        setSessionKey(existingSession)
        setHasInitialized(true)
        return existingSession
      }
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [hasInitialized, sessionKey, isSignedIn, getToken, user])

  const refreshSession = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      let clerkToken: string | undefined

      // Get Clerk token if user is signed in
      if (isSignedIn && getToken) {
        clerkToken = (await getToken()) || undefined
        if (IS_DEV) console.log("[useSession] Got Clerk token for authenticated user")
      }

      if (IS_DEV) console.log("[useSession] Refreshing session (forced)")

      // Force a fresh session from the backend
      const session = await ensureSession(
        clerkToken,
        user?.primaryEmailAddress?.emailAddress,
        user?.firstName || undefined,
        user?.lastName || undefined
      )
      if (IS_DEV) console.log("[useSession] Session refreshed successfully", { session })
      setSessionKey(session)
      return session
    } catch (err) {
      console.error("[useSession] Failed to refresh session:", err)
      setError(err instanceof Error ? err : new Error("Unknown error"))
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [isSignedIn, getToken, user])

  // Auto-initialize on mount if enabled
  useEffect(() => {
    if (autoInitialize && !hasInitialized) {
      if (IS_DEV) console.log("[useSession] Auto-initializing session")
      initializeSession()
    }
  }, [autoInitialize, hasInitialized, initializeSession])

  // Check for existing session in localStorage on mount
  useEffect(() => {
    const existingSession = getSessionKey()
    if (existingSession && !sessionKey) {
      if (IS_DEV) console.log("[useSession] Found existing session in localStorage", { existingSession })
      setSessionKey(existingSession)
      setHasInitialized(true)
    }
  }, [sessionKey])

  // Listen for localStorage changes (when session changes in same tab)
  useEffect(() => {
    const handleStorageChange = () => {
      const newSession = getSessionKey()
      if (newSession && newSession !== sessionKey) {
        if (IS_DEV) console.log("[useSession] Session changed in localStorage, updating", {
          old: sessionKey?.substring(0, 8),
          new: newSession.substring(0, 8),
        })
        setSessionKey(newSession)
      }
    }

    // Check periodically for localStorage changes (storage event doesn't fire in same tab)
    const interval = setInterval(handleStorageChange, 1000)

    // Also listen for storage events from other tabs
    window.addEventListener("storage", handleStorageChange)

    return () => {
      clearInterval(interval)
      window.removeEventListener("storage", handleStorageChange)
    }
  }, [sessionKey])

  return {
    sessionKey,
    isLoading,
    error,
    isAnonymous: !isSignedIn,
    initializeSession,
    refreshSession,
  }
}
