"use client"

import { useEffect } from "react"

/**
 * Defines backward-compatible globals expected by older builds to prevent
 * ReferenceError crashes when loading cached client bundles.
 */
export function InitGlobals() {
  useEffect(() => {
    if (typeof window === "undefined") return
    const w = window as any

    // Provide a no-op setter for legacy callers and keep a simple value store.
    if (typeof w.lastUploadProgress === "undefined") {
      w.lastUploadProgress = 0
    }
    if (typeof w.setLastUploadProgress !== "function") {
      w.setLastUploadProgress = (v: number) => {
        w.lastUploadProgress = v
      }
    }
  }, [])

  return null
}

