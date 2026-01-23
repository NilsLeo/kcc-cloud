const LICENSE_KEY = "mangaconverter_session_key"
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5500"

/**
 * Get session key from localStorage
 */
export function getSessionKey(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(LICENSE_KEY)
}

/**
 * Set session key in localStorage
 */
export function setSessionKey(sessionKey: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(LICENSE_KEY, sessionKey)
}

/**
 * Remove session key from localStorage
 */
export function removeSessionKey(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(LICENSE_KEY)
}

/**
 * Get or create anonymous session
 * This is called on first visit for anonymous users
 */
export async function getOrCreateAnonymousSession(): Promise<string> {
  // Check if we already have a session in localStorage
  const existingSession = getSessionKey()
  if (existingSession) {
    return existingSession
  }

  // Create new anonymous session via backend
  try {
    const response = await fetch(`${API_BASE_URL}/register`, {
      method: "GET",
    })

    const data = await response.json()
    if (data.success && data.session_key) {
      setSessionKey(data.session_key)
      return data.session_key
    }

    throw new Error(data.error || "Failed to create session")
  } catch (error) {
    console.error("Error creating anonymous session:", error)
    throw error
  }
}

/**
 * Claim an anonymous session for an authenticated Clerk user
 * This is called after sign-up or sign-in
 */
export async function claimLicense(
  anonymousLicenseKey: string,
  clerkToken: string,
  email?: string,
  firstName?: string,
  lastName?: string
): Promise<{ success: boolean; session_key: string; jobs_merged?: number }> {
  console.log('[claimLicense] Calling claim-session endpoint', {
    url: `${API_BASE_URL}/api/auth/claim-session`,
    hasToken: !!clerkToken,
    anonymousLicenseKey: anonymousLicenseKey.substring(0, 8) + '...',
    email
  })

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/claim-session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${clerkToken}`,
      },
      body: JSON.stringify({
        session_key: anonymousLicenseKey,
        email,
        first_name: firstName,
        last_name: lastName,
      }),
    })

    console.log('[claimLicense] Response status:', response.status)
    const data = await response.json()
    console.log('[claimLicense] Response data:', data)

    if (data.success) {
      // Update localStorage with the claimed session (might be same or merged)
      setSessionKey(data.session_key)
      console.log("[claimLicense] Session claimed successfully:", data)
      return data
    }

    throw new Error(data.error || "Failed to claim session")
  } catch (error) {
    console.error("[claimLicense] Error claiming session:", error)
    throw error
  }
}

/**
 * Get or create session for authenticated Clerk user
 * This is called when a user signs in without an anonymous session
 */
export async function getOrCreateUserLicense(
  clerkToken: string,
  email?: string,
  firstName?: string,
  lastName?: string
): Promise<string> {
  console.log('[getOrCreateUserLicense] Calling get-or-create-session endpoint', {
    url: `${API_BASE_URL}/api/auth/get-or-create-session`,
    hasToken: !!clerkToken,
    email
  })

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/get-or-create-session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${clerkToken}`,
      },
      body: JSON.stringify({
        email,
        first_name: firstName,
        last_name: lastName,
      }),
    })

    console.log('[getOrCreateUserLicense] Response status:', response.status)
    const data = await response.json()
    console.log('[getOrCreateUserLicense] Response data:', data)

    if (data.success && data.session_key) {
      setSessionKey(data.session_key)
      console.log('[getOrCreateUserLicense] Session created/retrieved successfully')
      return data.session_key
    }

    throw new Error(data.error || "Failed to get or create session")
  } catch (error) {
    console.error("[getOrCreateUserLicense] Error getting/creating user session:", error)
    throw error
  }
}

/**
 * Ensure user has a valid session
 * Handles both anonymous and authenticated users
 */
export async function ensureSession(
  clerkToken?: string,
  email?: string,
  firstName?: string,
  lastName?: string
): Promise<string> {
  const existingSession = getSessionKey()

  console.log('[ensureSession] Called with', {
    hasToken: !!clerkToken,
    hasExistingSession: !!existingSession,
    existingSession: existingSession?.substring(0, 8) + '...',
    email
  })

  if (clerkToken) {
    // Authenticated user
    console.log('[ensureSession] User is authenticated')

    if (existingSession) {
      // Try to claim the anonymous session
      console.log('[ensureSession] Attempting to claim existing session')
      try {
        const result = await claimLicense(existingSession, clerkToken, email, firstName, lastName)
        console.log('[ensureSession] Session claimed successfully', result)
        return result.session_key
      } catch (error) {
        // If claiming fails, get or create a new session
        console.warn("[ensureSession] Failed to claim session, creating new one:", error)
        return await getOrCreateUserLicense(clerkToken, email, firstName, lastName)
      }
    } else {
      // No existing session, create one for the user
      console.log('[ensureSession] No existing session, creating new one for authenticated user')
      return await getOrCreateUserLicense(clerkToken, email, firstName, lastName)
    }
  } else {
    // Anonymous user
    console.log('[ensureSession] User is anonymous, creating anonymous session')
    return await getOrCreateAnonymousSession()
  }
}
