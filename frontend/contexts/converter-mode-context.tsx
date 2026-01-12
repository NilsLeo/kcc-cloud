"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"

type ConverterMode = "manga" | "comic"

interface ConverterModeContextType {
  mode: ConverterMode
  setMode: (mode: ConverterMode) => void
  isComic: boolean
  isManga: boolean
  toggleMode: () => void
}

const ConverterModeContext = createContext<ConverterModeContextType>({
  mode: "manga",
  setMode: () => {},
  isComic: false,
  isManga: true,
  toggleMode: () => {},
})

export function ConverterModeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ConverterMode>("manga")
  const [initialized, setInitialized] = useState(false)

  // Determine initial mode based on URL and localStorage
  useEffect(() => {
    // Only run this once on client-side
    if (initialized) return

    // Check if we're in a browser environment
    if (typeof window !== "undefined") {
      // First check URL to determine default mode
      const hostname = window.location.hostname.toLowerCase()
      const isComicDomain = hostname.includes("comicconverter")
      const isMangaDomain = hostname.includes("mangaconverter")

      // Then check localStorage for user preference
      const savedMode = localStorage.getItem("converterMode") as ConverterMode

      if (savedMode && (savedMode === "manga" || savedMode === "comic")) {
        // User preference takes precedence
        setMode(savedMode)
      } else if (isComicDomain) {
        // No saved preference, but we're on comic domain
        setMode("comic")
      } else if (isMangaDomain) {
        // No saved preference, but we're on manga domain
        setMode("manga")
      }
      // If neither, default is already "manga"

      setInitialized(true)
    }
  }, [initialized])

  // Save mode to localStorage when it changes
  useEffect(() => {
    if (initialized && typeof window !== "undefined") {
      localStorage.setItem("converterMode", mode)
    }
  }, [mode, initialized])

  const toggleMode = () => {
    setMode((prevMode) => (prevMode === "manga" ? "comic" : "manga"))
  }

  const value = {
    mode,
    setMode,
    isComic: mode === "comic",
    isManga: mode === "manga",
    toggleMode,
  }

  return <ConverterModeContext.Provider value={value}>{children}</ConverterModeContext.Provider>
}

export function useConverterMode() {
  return useContext(ConverterModeContext)
}
