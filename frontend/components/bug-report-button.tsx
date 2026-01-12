"use client"

import { useState } from "react"
import { Bug, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"

export function BugReportButton() {
  const [isOpen, setIsOpen] = useState(false)

  const handleEmailClick = () => {
    window.location.href = "mailto:support@mangaconverter.com?subject=Bug Report - MangaConverter"
    setIsOpen(false)
  }

  return (
    <>
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogTrigger asChild>
          <Button
            size="lg"
            className="fixed bottom-6 right-6 z-50 h-14 px-6 shadow-lg hover:shadow-xl transition-all duration-300 gap-2 group bg-orange-600 hover:bg-orange-700 text-white"
            variant="default"
          >
            <Bug className="h-5 w-5 group-hover:rotate-12 transition-transform" />
            <span className="font-semibold">Report a Bug</span>
            <Badge variant="secondary" className="ml-1 bg-white/20 text-white border-0">
              Beta
            </Badge>
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-2xl">
              <Bug className="h-6 w-6 text-orange-600" />
              Report a Bug
            </DialogTitle>
            <DialogDescription className="text-base pt-2">
              This app is in early development. We're grateful for any bugs, errors, or feedback you can share!
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="rounded-lg border bg-muted/50 p-4 space-y-3">
              <p className="text-sm text-muted-foreground">
                Click the button below to open your email client and send us a bug report:
              </p>
              <Button onClick={handleEmailClick} className="w-full gap-2 bg-orange-600 hover:bg-orange-700" size="lg">
                <Mail className="h-4 w-4" />
                Email support@mangaconverter.com
              </Button>
            </div>
            <div className="text-xs text-muted-foreground space-y-1">
              <p className="font-medium">Please include:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>What you were trying to do</li>
                <li>What happened instead</li>
                <li>Your device/browser information</li>
                <li>Any error messages you saw</li>
              </ul>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
