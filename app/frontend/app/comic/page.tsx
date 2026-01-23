"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useConverterMode } from "@/contexts/converter-mode-context"

export default function ComicPage() {
  const router = useRouter()
  const { setMode } = useConverterMode()

  useEffect(() => {
    // Set mode to comic and redirect to home
    setMode("comic")
    router.replace("/")
  }, [router, setMode])

  return null
}
