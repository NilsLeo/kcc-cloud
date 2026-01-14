"use client"

import { useEffect } from "react"

interface StructuredDataProps {
  contentType: "comic" | "manga"
}

export function StructuredData({ contentType }: StructuredDataProps) {
  useEffect(() => {
    const siteName = "Comic & Manga Converter"

    const existingScript = document.getElementById("structured-data")
    if (existingScript) {
      existingScript.remove()
    }

    const script = document.createElement("script")
    script.id = "structured-data"
    script.type = "application/ld+json"
    script.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "WebApplication",
      name: siteName,
      url: "https://mangaconverter.com",
      applicationCategory: "Utility",
      operatingSystem: "Web",
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
      },
      description: `Free online tool to convert ${contentType} files to e-reader formats like EPUB, MOBI, and CBZ. Optimized for Kindle, Kobo, and other e-readers.`,
      browserRequirements: "Requires JavaScript. Requires HTML5.",
      softwareVersion: "1.0",
      author: {
        "@type": "Organization",
        name: "Converter Team",
      },
      potentialAction: {
        "@type": "UseAction",
        target: {
          "@type": "EntryPoint",
          urlTemplate: "https://mangaconverter.com",
        },
        expectsAcceptanceOf: {
          "@type": "Offer",
          price: "0",
          priceCurrency: "USD",
        },
      },
    })

    document.head.appendChild(script)

    return () => {
      const scriptToRemove = document.getElementById("structured-data")
      if (scriptToRemove) {
        scriptToRemove.remove()
      }
    }
  }, [contentType])

  return null
}
