"use client"

import { cn } from "@/lib/utils"
import { useConverterMode } from "@/contexts/converter-mode-context"
import { useState, useEffect } from "react"
import Image from "next/image"

interface LogoProps {
  className?: string
  size?: "sm" | "md" | "lg"
}

const APP_TITLE = process.env.NEXT_PUBLIC_APP_TITLE || "KCC Cloud"

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

  const iconSizes = {
    sm: 20,
    md: 28,
    lg: 32,
  }

  // Split title into first word and remaining words
  const words = APP_TITLE.split(" ")
  const firstWord = words[0]
  const remainingWords = words.slice(1).join(" ")

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Image
        src="/favicon.svg"
        alt=""
        width={iconSizes[size]}
        height={iconSizes[size]}
        className="flex-shrink-0"
      />
      <h1 className={cn("font-semibold tracking-tight font-poppins", sizes[size])}>
        <span className="text-foreground">{firstWord}</span>
        {remainingWords && <span className="text-theme-medium"> {remainingWords}</span>}
      </h1>
    </div>
  )
}
