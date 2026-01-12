"use client"

import type { FC } from "react"
import { useEffect, useRef } from "react"
import { MangaConverter } from "@/components/manga-converter"
import { ThemeToggle } from "@/components/theme-toggle"
import { Logo } from "@/components/logo"
import { DynamicTitle } from "@/components/dynamic-title"
import { StructuredData } from "@/components/structured-data"
import { Navbar } from "@/components/navbar"
import { useConverterMode } from "@/contexts/converter-mode-context"
import { useSession } from "@/hooks/use-session"

const HomePage: FC = () => {
  const { mode } = useConverterMode()
  const contentType = mode === "manga" ? "manga" : "comic"
  const themeClass = mode === "manga" ? "manga-theme" : "comic-theme"

  // Lazy session initialization - only create session on real user interaction
  const { initializeSession } = useSession({ autoInitialize: false })
  const sessionInitializedRef = useRef(false)

  useEffect(() => {
    // Initialize session on first real user interaction (not bot behavior)
    const initOnInteraction = (event: Event) => {
      if (!sessionInitializedRef.current) {
        sessionInitializedRef.current = true
        const eventType = event.type
        console.log(
          `🎯 [SESSION CREATED] User interaction detected (${eventType}) - Creating new session to avoid bot pollution`,
        )
        initializeSession()

        // Remove listeners after first trigger
        window.removeEventListener("mousemove", initOnInteraction)
        window.removeEventListener("touchstart", initOnInteraction)
        window.removeEventListener("click", initOnInteraction)
        window.removeEventListener("keydown", initOnInteraction)
      }
    }

    // Listen for real user interactions
    // Note: { once: true } doesn't work well with multiple listeners, so we manually remove them
    window.addEventListener("mousemove", initOnInteraction)
    window.addEventListener("touchstart", initOnInteraction) // Mobile users
    window.addEventListener("click", initOnInteraction)
    window.addEventListener("keydown", initOnInteraction) // Keyboard navigation

    console.log("[HomePage] Interaction listeners registered - waiting for user interaction")

    return () => {
      // Cleanup listeners on unmount
      window.removeEventListener("mousemove", initOnInteraction)
      window.removeEventListener("touchstart", initOnInteraction)
      window.removeEventListener("click", initOnInteraction)
      window.removeEventListener("keydown", initOnInteraction)
    }
  }, [initializeSession])

  return (
    <div className={`min-h-screen bg-background flex flex-col ${themeClass}`}>
      <DynamicTitle contentType={contentType} />
      <StructuredData contentType={contentType} />
      <header className="border-b sticky top-0 z-50 bg-background">
        <div className="container mx-auto px-4 py-4 md:py-5 flex justify-between items-center">
          <Logo />
          <div className="flex items-center gap-4">
            <Navbar />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="flex-1 container mx-auto px-4 py-8" role="main">
        <MangaConverter contentType={contentType} />
      </main>
    </div>
  )
}

export default HomePage
