"use client"

import { useState, useRef } from "react"
import { fetchWithLicense } from "@/lib/utils"
import { logError } from "@/lib/logger"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, FileText, Check, Loader2, X, Clock, ArrowRight, HardDrive } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"

export type ConvertedFileInfo = {
  id: string
  originalName: string
  convertedName: string
  downloadId: string
  timestamp: number
  device: string
  size?: number // Output file size
  inputFileSize?: number // Input file size
  actualDuration?: number // Duration in seconds
}

interface ConvertedFilesProps {
  files: ConvertedFileInfo[]
  onClearAll: () => void
  onRemoveFile?: (file: ConvertedFileInfo) => void
}

export function ConvertedFiles({ files, onClearAll, onRemoveFile }: ConvertedFilesProps) {
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({})
  // Use a ref to store download links to prevent them from being garbage collected
  const downloadLinksRef = useRef<HTMLAnchorElement[]>([])

  if (files.length === 0) return null

  // Helper function to remove file extension for display
  const removeExtension = (filename: string) => {
    return filename.replace(/\.[^/.]+$/, "")
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "Unknown size"
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return null

    if (seconds < 60) {
      return `${Math.round(seconds)}s`
    }

    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)

    if (remainingSeconds === 0) {
      return `${minutes}m`
    }

    return `${minutes}m ${remainingSeconds}s`
  }

  const downloadFile = async (file: ConvertedFileInfo) => {
    try {
      setDownloadingFiles((prev) => ({ ...prev, [file.id]: true }))

      // Request a signed download URL from the API
      const response = await fetchWithLicense(`/api/download/${file.downloadId}`)
      if (!response.ok) {
        const errText = await response.text()
        throw new Error(errText || "Failed to get download URL")
      }
      const data = await response.json()
      if (!data.signedUrl) {
        throw new Error(data.error || "No download URL returned")
      }
      // Redirect browser to the signed URL to download
      window.location.href = data.signedUrl
      toast.success(`Downloading ${file.convertedName}`)
    } catch (error) {
      logError("Download error", file.downloadId, { error: error.message, error, fileId: file.id })
      toast.error("Download failed", {
        description: error instanceof Error ? error.message : "Failed to download file",
      })
    } finally {
      // Set downloading to false after a short delay
      setTimeout(() => {
        setDownloadingFiles((prev) => ({ ...prev, [file.id]: false }))
      }, 1000)
    }
  }

  return (
    <Card className="mb-8">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-full bg-success/10">
              <Check className="h-4 w-4 text-success" />
            </div>
            <CardTitle>Converted Files</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearAll}
            disabled={Object.values(downloadingFiles).some((v) => v)}
          >
            Clear All
          </Button>
        </div>
        <CardDescription>Your successfully converted files ready for download</CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          <AnimatePresence>
            {files.map((file) => (
              <motion.div
                key={file.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className="group relative rounded-lg border bg-card hover:bg-accent/50 transition-all duration-200 overflow-hidden"
              >
                <div className="flex items-start gap-4 p-4">
                  {/* File icon */}
                  <div className="p-2.5 rounded-lg bg-primary/10 text-primary shrink-0">
                    <FileText className="h-5 w-5" />
                  </div>

                  {/* File info */}
                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Filename */}
                    <div>
                      <p className="font-semibold text-base truncate">{file.convertedName}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <span>{formatDate(file.timestamp)}</span>
                        <span>•</span>
                        <Badge variant="secondary" className="text-xs font-normal">
                          {file.device}
                        </Badge>
                      </div>
                    </div>

                    {/* File size and duration info */}
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      {/* File size conversion */}
                      {file.inputFileSize && file.size ? (
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <HardDrive className="h-3.5 w-3.5" />
                          <span className="font-medium">{formatFileSize(file.inputFileSize)}</span>
                          <ArrowRight className="h-3 w-3" />
                          <span className="font-medium text-foreground">{formatFileSize(file.size)}</span>
                        </div>
                      ) : file.size ? (
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <HardDrive className="h-3.5 w-3.5" />
                          <span className="font-medium">{formatFileSize(file.size)}</span>
                        </div>
                      ) : null}

                      {/* Duration */}
                      {file.actualDuration && (
                        <>
                          <span className="text-muted-foreground">•</span>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Clock className="h-3.5 w-3.5" />
                            <span className="font-medium">{formatDuration(file.actualDuration)}</span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      onClick={() => downloadFile(file)}
                      disabled={downloadingFiles[file.id]}
                      size="default"
                      className="shadow-sm"
                      aria-label={`Download ${file.convertedName}`}
                    >
                      {downloadingFiles[file.id] ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Downloading
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-2" />
                          Download
                        </>
                      )}
                    </Button>

                    {onRemoveFile && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onRemoveFile(file)}
                        aria-label={`Remove ${file.convertedName}`}
                        className="text-muted-foreground hover:text-destructive"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}
