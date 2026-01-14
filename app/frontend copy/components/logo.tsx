"use client"

import { cn } from "@/lib/utils"
import { useConverterMode } from "@/contexts/converter-mode-context"
import { useState, useEffect } from "react"

interface LogoProps {
  className?: string
  size?: "sm" | "md" | "lg"
}

export function Logo({ className, size = "md" }: LogoProps) {
  const { isComic } = useConverterMode()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const sizes = {
    sm: "text-base",
    md: "text-xl",
    lg: "text-2xl",
  }

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <h1 className={cn("font-bold tracking-tight", sizes[size])}>
        <span className="text-foreground">Manga & Comic</span> <span className="text-theme-medium">Converter</span>
      </h1>
    </div>
  )
}
