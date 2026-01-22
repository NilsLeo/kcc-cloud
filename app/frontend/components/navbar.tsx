"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Download, Upload, Menu, X, Star } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

const GITHUB_REPO_URL = "https://github.com/NilsLeo/kcc-cloud"

export function Navbar() {
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const navLinks = [
    {
      href: "/",
      label: "Converter",
      icon: Upload,
      active: pathname === "/" || pathname === "/manga" || pathname === "/comic",
    },
    {
      href: "/downloads",
      label: "My Downloads",
      icon: Download,
      active: pathname === "/downloads",
    },
  ]

  return (
    <nav className="flex items-center gap-2">
      {/* Desktop Navigation */}
      <div className="hidden md:flex items-center gap-6">
        {navLinks.map((link) => {
          const Icon = link.icon
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary",
                link.active ? "text-foreground" : "text-muted-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{link.label}</span>
            </Link>
          )
        })}
      </div>

      {/* GitHub Star Button - Desktop */}
      <div className="hidden md:block">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <a
                href={GITHUB_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20 hover:border-amber-500/50 transition-colors"
              >
                <Star className="h-3.5 w-3.5 fill-current" />
                <span>Star</span>
              </a>
            </TooltipTrigger>
            <TooltipContent>
              <p>Star us on GitHub</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Mobile Navigation */}
      <div className="md:hidden">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="h-9 w-9"
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>

        {mobileMenuOpen && (
          <div className="absolute left-0 right-0 top-16 bg-background border-b shadow-lg z-50">
            <div className="container py-4 space-y-2">
              {navLinks.map((link) => {
                const Icon = link.icon
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors hover:bg-muted",
                      link.active ? "text-foreground bg-muted" : "text-muted-foreground",
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{link.label}</span>
                  </Link>
                )
              })}
              
              {/* GitHub Star - Mobile */}
              <a
                href={GITHUB_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors hover:bg-muted text-amber-600 dark:text-amber-400"
              >
                <Star className="h-5 w-5 fill-current" />
                <span>Star on GitHub</span>
              </a>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
