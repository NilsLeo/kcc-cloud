"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Keyboard } from "lucide-react"

export function KeyboardShortcuts() {
  const [isOpen, setIsOpen] = useState(false)

  // Set up keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle keyboard shortcuts when not in an input, textarea, etc.
      if (e.target instanceof HTMLElement) {
        const tagName = e.target.tagName.toLowerCase()
        if (tagName === "input" || tagName === "textarea" || tagName === "select") {
          return
        }
      }

      // Shift + ? to open shortcuts dialog
      if (e.shiftKey && e.key === "?") {
        setIsOpen(true)
      }

      // Escape to close shortcuts dialog
      if (e.key === "Escape") {
        setIsOpen(false)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  const shortcuts = [
    { key: "Shift + ?", description: "Show keyboard shortcuts" },
    { key: "u", description: "Go to Upload tab" },
    { key: "d", description: "Go to Device & Options tab" },
    { key: "q", description: "Go to Queue & Convert tab" },
    { key: "c", description: "Start conversion (when in Queue tab)" },
    { key: "Esc", description: "Close dialogs" },
    { key: "Space", description: "Toggle advanced options" },
  ]

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Keyboard shortcuts">
          <Keyboard className="h-5 w-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>Use these keyboard shortcuts to navigate the app more efficiently</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="flex items-center justify-between">
              <span className="text-muted-foreground">{shortcut.description}</span>
              <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
