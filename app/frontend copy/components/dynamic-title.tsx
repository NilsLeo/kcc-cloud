"use client"

import { useEffect } from "react"

interface DynamicTitleProps {
  contentType: "comic" | "manga"
}

export function DynamicTitle({ contentType }: DynamicTitleProps) {
  useEffect(() => {
    const siteName = "MangaConverter.com"
    const type = contentType === "comic" ? "Comic" : "Manga"

    document.title = `${type} Converter | ${siteName}`

    const metaDescription = document.querySelector('meta[name="description"]')
    if (metaDescription) {
      metaDescription.setAttribute(
        "content",
        `Free online tool to convert ${contentType} files to e-reader formats like EPUB, MOBI, and CBZ. Optimized for Kindle, Kobo, and other e-readers with perfect formatting.`,
      )
    }
  }, [contentType])

  return null
}
