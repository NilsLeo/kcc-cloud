"use client"

import { Bug, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function BugReportCard() {
  const handleEmailClick = () => {
    window.location.href =
      "mailto:support@mangaconverter.com?subject=Bug Report - MangaConverter&body=Please describe the bug or issue you encountered:%0D%0A%0D%0A"
  }

  return (
    <Card className="border-2 border bg-muted/50 dark:bg-muted/20">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Bug className="h-5 w-5 text-foreground" />
          <CardTitle className="flex items-center gap-2">
            Help Us Improve
            <span className="inline-flex items-center rounded-full bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground">
              Beta
            </span>
          </CardTitle>
        </div>
        <CardDescription>
          This app is in early development. We're grateful for any bugs, errors, or feedback you can share!
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          onClick={handleEmailClick}
          className="w-full gap-2 text-base font-semibold bg-theme-medium hover:bg-theme-dark"
          size="lg"
        >
          <Mail className="h-5 w-5" />
          Report a Bug or Issue
        </Button>
        <p className="text-xs text-muted-foreground text-center mt-3">Email: support@mangaconverter.com</p>
      </CardContent>
    </Card>
  )
}
