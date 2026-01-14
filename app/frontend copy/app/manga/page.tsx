"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useConverterMode } from "@/contexts/converter-mode-context"

export default function MangaPage() {
  const router = useRouter()
  const { setMode } = useConverterMode()

  useEffect(() => {
    // Set mode to manga and redirect to home
    setMode("manga")
    router.replace("/")
  }, [router, setMode])

  return null
}
