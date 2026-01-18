"use client"

import { useState, useRef } from "react"
import { fetchWithLicense } from "@/lib/utils"
import { logError } from "@/lib/logger"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, FileText, Check, Loader2, Trash2, Clock, ArrowRight, HardDrive } from "lucide-react"
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
  size?: number
  inputFileSize?: number
  actualDuration?: number
}

interface ConvertedFilesProps {
  files: ConvertedFileInfo[]
  onClearAll: () => void
  onRemoveFile?: (file: ConvertedFileInfo) => void
}

const MOCK_DATA: ConvertedFileInfo[] = [
  {
    id: "mock-1",
    originalName: "chapter-05.cbz",
    convertedName: "chapter-05.epub",
    downloadId: "dl-mock-1",
    timestamp: Date.now() - 3600000,
    device: "Kindle",
    size: 8450000,
    inputFileSize: 12300000,
    actualDuration: 45,
  },
  {
    id: "mock-2",
    originalName: "volume-03.cbr",
    convertedName: "volume-03.mobi",
    downloadId: "dl-mock-2",
    timestamp: Date.now() - 7200000,
    device: "Kobo",
    size: 15600000,
    inputFileSize: 23400000,
    actualDuration: 78,
  },
  {
    id: "mock-3",
    originalName: "manga-collection.zip",
    convertedName: "manga-collection.pdf",
    downloadId: "dl-mock-3",
    timestamp: Date.now() - 10800000,
    device: "iPad",
    size: 45200000,
    inputFileSize: 52100000,
    actualDuration: 132,
  },
]

export function ConvertedFiles({ files, onClearAll, onRemoveFile }: ConvertedFilesProps) {
  const apiUrl = "http://localhost:8060"
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({})
  const downloadLinksRef = useRef<HTMLAnchorElement[]>([])

  const displayFiles = files.length > 0 ? files : MOCK_DATA
  const usingMockData = files.length === 0

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
    if (usingMockData) {
      console.log("[v0] Using mock data, simulating download...")
      setDownloadingFiles((prev) => ({ ...prev, [file.id]: true }))
      await new Promise((resolve) => setTimeout(resolve, 1500))
      toast.success(`Mock download: ${file.convertedName}`)
      setDownloadingFiles((prev) => ({ ...prev, [file.id]: false }))
      return
    }

    try {
      setDownloadingFiles((prev) => ({ ...prev, [file.id]: true }))

      console.log("[v0] Attempting download from localhost:8060...")
      const response = await fetchWithLicense(`${apiUrl}/download/${file.downloadId}`)
      if (!response.ok) {
        const errText = await response.text()
        throw new Error(errText || "Failed to download file")
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = file.convertedName
      link.style.display = "none"
      document.body.appendChild(link)
      downloadLinksRef.current.push(link)
      link.click()

      setTimeout(() => {
        window.URL.revokeObjectURL(url)
        document.body.removeChild(link)
      }, 100)

      toast.success(`Downloading ${file.convertedName}`)
    } catch (error) {
      console.log("[v0] Download failed, localhost:8060 not reachable", {
        error: error instanceof Error ? error.message : String(error),
      })
      logError("Download error", file.downloadId, { error: error.message, error, fileId: file.id })
      toast.error("Download failed", {
        description: error instanceof Error ? error.message : "Failed to download file",
      })
    } finally {
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
        <CardDescription>
          Your successfully converted files ready for download
          {usingMockData && (
            <Badge variant="outline" className="ml-2 text-xs">
              Demo Mode
            </Badge>
          )}
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          <AnimatePresence>
            {displayFiles.map((file) => (
              <motion.div
                key={file.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className="group relative rounded-lg border bg-card transition-all duration-200 overflow-hidden"
              >
                <div className="flex items-start gap-4 p-4">
                  <div className="p-2.5 rounded-lg bg-primary/10 text-primary shrink-0">
                    <FileText className="h-5 w-5" />
                  </div>

                  <div className="flex-1 min-w-0 space-y-2">
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

                    <div className="flex flex-wrap items-center gap-3 text-sm">
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
                </div>

                <div className="flex items-center justify-between px-4 py-3 border-t bg-muted/30">
                  <div className="text-xs text-muted-foreground">Ready for download</div>
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => downloadFile(file)}
                      disabled={downloadingFiles[file.id]}
                      size="sm"
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
                        className="h-9 w-9 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-4 w-4" />
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
