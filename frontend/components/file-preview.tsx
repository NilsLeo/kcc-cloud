"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { X, ChevronLeft, ChevronRight, Loader2 } from "lucide-react"

interface FilePreviewProps {
  file: File
  onClose: () => void
}

export function FilePreview({ file, onClose }: FilePreviewProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [pages, setPages] = useState<string[]>([])
  const [currentPage, setCurrentPage] = useState(0)

  useEffect(() => {
    // This is a simplified preview that works for image files
    // In a real app, you'd need more sophisticated handling for CBZ, PDF, etc.
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file)
      setPages([url])
      setIsLoading(false)

      return () => {
        URL.revokeObjectURL(url)
      }
    } else {
      // Simulate loading pages from a comic/manga file
      setIsLoading(true)

      // This is just a simulation - in a real app you'd extract pages from CBZ/PDF
      setTimeout(() => {
        // Create dummy pages for preview
        const dummyPages = Array(5)
          .fill(0)
          .map((_, i) => `/placeholder.svg?height=800&width=600&text=Page ${i + 1}`)
        setPages(dummyPages)
        setIsLoading(false)
      }, 1500)
    }
  }, [file])

  const nextPage = () => {
    if (currentPage < pages.length - 1) {
      setCurrentPage((prev) => prev + 1)
    }
  }

  const prevPage = () => {
    if (currentPage > 0) {
      setCurrentPage((prev) => prev - 1)
    }
  }

  // Set up keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        nextPage()
      } else if (e.key === "ArrowLeft") {
        prevPage()
      } else if (e.key === "Escape") {
        onClose()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [currentPage, pages.length, onClose])

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] flex flex-col">
        <DialogHeader className="flex flex-row items-center justify-between">
          <DialogTitle>
            {file.name} {pages.length > 1 && `(Page ${currentPage + 1}/${pages.length})`}
          </DialogTitle>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close preview">
            <X className="h-4 w-4" />
          </Button>
        </DialogHeader>

        <div className="flex-1 overflow-hidden relative flex items-center justify-center bg-black/5 dark:bg-white/5 rounded-md">
          {isLoading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading preview...</p>
            </div>
          ) : (
            <>
              {pages.length > 0 ? (
                <img
                  src={pages[currentPage] || "/placeholder.svg"}
                  alt={`Page ${currentPage + 1} of ${file.name}`}
                  className="max-h-[70vh] max-w-full object-contain"
                />
              ) : (
                <div className="text-center p-8">
                  <p>Preview not available for this file type</p>
                </div>
              )}

              {pages.length > 1 && (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute left-2 top-1/2 -translate-y-1/2 bg-background/80 hover:bg-background"
                    onClick={prevPage}
                    disabled={currentPage === 0}
                    aria-label="Previous page"
                  >
                    <ChevronLeft className="h-6 w-6" />
                  </Button>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-2 top-1/2 -translate-y-1/2 bg-background/80 hover:bg-background"
                    onClick={nextPage}
                    disabled={currentPage === pages.length - 1}
                    aria-label="Next page"
                  >
                    <ChevronRight className="h-6 w-6" />
                  </Button>
                </>
              )}
            </>
          )}
        </div>

        <div className="flex justify-between items-center pt-4">
          <div className="text-sm text-muted-foreground">
            {file.type || "Unknown file type"} • {formatFileSize(file.size)}
          </div>

          {pages.length > 1 && (
            <div className="flex gap-1">
              {pages.map((_, i) => (
                <div
                  key={i}
                  className={`h-1.5 w-3 rounded-full cursor-pointer ${i === currentPage ? "bg-primary" : "bg-muted"}`}
                  onClick={() => setCurrentPage(i)}
                  role="button"
                  tabIndex={0}
                  aria-label={`Go to page ${i + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return "0 Bytes"
  const k = 1024
  const sizes = ["Bytes", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
}
