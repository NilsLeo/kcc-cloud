"use client"

import { useConverterMode } from "@/contexts/converter-mode-context"
import { BugReportCard } from "./bug-report-card"
import { SupportCard } from "./support-card"

export function Footer() {
  const { isComic } = useConverterMode()
  const siteName = "MangaConverter.com"
  const contentType = isComic ? "comic" : "manga"

  return (
    <footer className="mt-12 pt-8 border-t text-sm text-muted-foreground">
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <SupportCard />
          <BugReportCard />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-2">About Comic & Manga Converter</h3>
            <p className="text-sm">
              {siteName} is a web application that helps you convert {contentType} files to e-reader formats. It
              supports various devices including Kindle, Kobo, and reMarkable.
            </p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Credits</h3>
            <p>
              Based on{" "}
              <a
                href="https://github.com/ciromattia/kcc"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline font-medium"
              >
                Kindle Comic Converter (KCC)
              </a>
              . Licensed under ISC Session.
            </p>
            <p className="text-xs mt-2">
              © 2012-2025 Ciro Mattia Gonano
              <br />© 2013-2019 Paweł Jastrzębski
              <br />© 2021-2023 Darodi
              <br />© 2023-2025 Alex Xu
            </p>
          </div>
        </div>

        <div itemScope itemType="https://schema.org/SoftwareApplication" className="hidden">
          <span itemProp="name">Comic & Manga Converter</span>
          <span itemProp="applicationCategory">Utility</span>
          <span itemProp="operatingSystem">Web</span>
          <div itemProp="offers" itemScope itemType="https://schema.org/Offer">
            <span itemProp="price">0</span>
            <span itemProp="priceCurrency">USD</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
