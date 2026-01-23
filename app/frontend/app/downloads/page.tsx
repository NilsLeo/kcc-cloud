"use client"

import type { FC } from "react"
import { MyDownloads } from "@/components/my-downloads"
import { DynamicTitle } from "@/components/dynamic-title"
import { StructuredData } from "@/components/structured-data"
import { Navbar } from "@/components/navbar"
import { Logo } from "@/components/logo"
import { ThemeToggle } from "@/components/theme-toggle"

const DownloadsPage: FC = () => {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <DynamicTitle contentType="downloads" />
      <StructuredData contentType="downloads" />
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
        <MyDownloads pageSize={10} />
      </main>
    </div>
  )
}

export default DownloadsPage
