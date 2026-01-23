import type React from "react"
import type { Metadata } from "next"
import localFont from "next/font/local"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "sonner"
import { ConverterModeProvider } from "@/contexts/converter-mode-context"
import { ErrorBoundary } from "@/components/error-boundary"
import { InitGlobals } from "@/components/init-globals"

// Avoid network fetches for Google Fonts in dev containers by relying on local fonts
// If you need Google fonts, switch back to next/font/google and ensure outbound network is available

const zenMaruGothic = localFont({
  src: [
    {
      path: "../fonts/ZenMaruGothic-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../fonts/ZenMaruGothic-Medium.ttf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../fonts/ZenMaruGothic-Black.ttf",
      weight: "900",
      style: "normal",
    },
  ],
  variable: "--font-zen-maru-gothic",
  display: "swap",
  preload: false,
})

const poppins = localFont({
  src: [
    {
      path: "../fonts/Poppins-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../fonts/Poppins-SemiBold.ttf",
      weight: "600",
      style: "normal",
    },
  ],
  variable: "--font-poppins",
  display: "swap",
  preload: false,
})

export const metadata: Metadata = {
  title: "Manga & Comic Converter | Convert Files for E-Readers",
  description:
    "Free online tool to convert manga and comic files to e-reader formats like EPUB, MOBI, and CBZ. Optimized for Kindle, Kobo, and other e-readers with perfect formatting.",
  keywords:
    "manga converter, comic converter, e-reader, kindle manga, kindle comics, kobo manga, kobo comics, convert cbz, convert pdf, manga to epub, comics to epub, manga to mobi, comics to mobi, free converter",
  authors: [{ name: "Converter Team" }],
  // Keep only non-duplicated icon entries here to avoid duplicate <link> tags
  icons: {
    other: [{ rel: "mask-icon", url: "/safari-pinned-tab.svg", color: "hsl(var(--theme-medium))" }],
  },
  openGraph: {
    title: "Manga & Comic Converter | Convert Files for E-Readers",
    description:
      "Free online tool to convert manga and comic files to e-reader formats like EPUB, MOBI, and CBZ. Optimized for Kindle, Kobo, and other e-readers with perfect formatting.",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Manga & Comic Converter | Convert Files for E-Readers",
    description:
      "Free online tool to convert manga and comic files to e-reader formats like EPUB, MOBI, and CBZ. Optimized for Kindle, Kobo, and other e-readers with perfect formatting.",
  },
  robots: {
    index: true,
    follow: true,
  },
  generator: "v0.dev",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
        <head>
          <link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96" />
          <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
          <link rel="shortcut icon" href="/favicon.ico" />
          <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
          <meta name="apple-mobile-web-app-title" content="MangaConverter" />
          <link rel="manifest" href="/site.webmanifest" />

          {/* Additional SEO meta tags */}
          <link rel="alternate" href="https://comicconverter.com" />
          <meta name="application-name" content="Manga & Comic Converter" />
          <meta name="apple-mobile-web-app-capable" content="yes" />
          <meta name="apple-mobile-web-app-status-bar-style" content="default" />
          {/* Title for iOS home screen added above; keep other PWA metas */}
          <meta name="format-detection" content="telephone=no" />
          <meta name="mobile-web-app-capable" content="yes" />
          <meta name="msapplication-TileColor" content="hsl(var(--theme-medium))" />
          <meta name="msapplication-tap-highlight" content="no" />
          <meta name="theme-color" content="hsl(var(--theme-medium))" />
        </head>
        <body className={`${zenMaruGothic.variable} ${poppins.variable} antialiased`}>
          {/* Define legacy globals as early as possible to avoid ReferenceError from cached bundles */}
          <script
            id="legacy-globals"
            dangerouslySetInnerHTML={{
              __html:
                "window.lastUploadProgress=window.lastUploadProgress||0;window.setLastUploadProgress=window.setLastUploadProgress||function(v){window.lastUploadProgress=v};",
            }}
          />
          <ErrorBoundary>
            <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
              <ConverterModeProvider>
                <InitGlobals />
                {children}
                <Toaster richColors position="top-center" />
              </ConverterModeProvider>
            </ThemeProvider>
          </ErrorBoundary>
        </body>
      </html>
  )
}
