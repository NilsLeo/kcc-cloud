"use client"

import type { FC } from "react"
import { MangaConverter } from "@/components/manga-converter"
import { ThemeToggle } from "@/components/theme-toggle"
import { Logo } from "@/components/logo"
import { DynamicTitle } from "@/components/dynamic-title"
import { StructuredData } from "@/components/structured-data"
import { Navbar } from "@/components/navbar"
import { useConverterMode } from "@/contexts/converter-mode-context"

const HomePage: FC = () => {
  const { mode } = useConverterMode()
  const contentType = mode === "manga" ? "manga" : "comic"
  const themeClass = mode === "manga" ? "manga-theme" : "comic-theme"


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
