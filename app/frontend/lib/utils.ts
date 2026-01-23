import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Function to generate a readable file size from bytes
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}

// FOSS version - simplified fetch without session management
export async function fetchWithLicense(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  return fetch(url, options)
}

// FOSS version - no session keys needed
export async function ensureSessionKey(force = false, retries = 3): Promise<string> {
  // Return empty string - not used in FOSS version
  return ""
}

// FOSS version - no session management
export function getSessionKey(): string | null {
  return null
}

export function setSessionKey(sessionKey: string): void {
  // No-op in FOSS version
}
