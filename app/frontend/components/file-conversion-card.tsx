"use client"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { toast } from "@/hooks/use-toast"
import { AlertCircle, Check, Download, Trash2, Upload, Settings, Clock, MoreVertical } from "lucide-react"
import { useState } from "react"

interface FileConversionCardProps {
  file: {
    id: string
    jobId?: string
    job_id?: string
    name: string
    size?: number
    status: string
    upload_progress?: {
      percentage: number
      uploaded_bytes?: number
    }
    processing_progress?: {
      eta_at?: string
      projected_eta?: number
    }
    processing_at?: string
    error?: string
    isConverted?: boolean
    device?: string
  }
  onDownload?: (file: any) => void
  onDelete?: (id: string) => void
  onCancel?: (id: string) => void
  onDismiss?: (id: string) => void
  showActions?: boolean
  isDownloading?: boolean
  context?: 'queue' | 'downloads'
}

export function FileConversionCard({
  file,
  onDownload,
  onDelete,
  onCancel,
  onDismiss,
  showActions = true,
  isDownloading = false,
  context = 'queue',
}: FileConversionCardProps) {
  const [isDeleting, setIsDeleting] = useState(false)

  const getStatusColors = () => {
    const status = file.status

    if (status === "COMPLETE") {
      return {
        bg: "bg-success/10",
        text: "text-success",
        progressBar: "bg-success",
      }
    }

    if (status === "ERROR") {
      return {
        bg: "bg-destructive/10",
        text: "text-destructive",
        progressBar: "bg-destructive",
      }
    }

    if (status === "PROCESSING") {
      return {
        bg: "bg-[hsl(var(--theme-medium))]/20",
        text: "text-[hsl(var(--theme-medium))]",
        progressBar: "bg-[hsl(var(--theme-medium))]",
      }
    }

    if (status === "QUEUED") {
      return {
        bg: "bg-[hsl(var(--theme-medium))]/20",
        text: "text-[hsl(var(--theme-medium))]",
        progressBar: "bg-[hsl(var(--theme-medium))]",
      }
    }

    if (status === "UPLOADING") {
      return {
        bg: "bg-[hsl(var(--theme-lightest))]/30",
        text: "text-[hsl(var(--theme-light))]",
        progressBar: "bg-[hsl(var(--theme-lightest))]",
      }
    }

    return {
      bg: "bg-muted",
      text: "text-muted-foreground",
      progressBar: "bg-muted",
    }
  }

  const statusColors = getStatusColors()

  const getFileIcon = () => {
    const extension = file.name.split(".").pop()?.toLowerCase()
    return extension || "file"
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "Unknown size"
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  const formatFileSizeMobile = (bytes?: number) => {
    if (!bytes) return "Unknown"
    const mb = bytes / (1024 * 1024)
    return `${Math.round(mb)} MB`
  }

  const computeProcessingPct = () => {
    const pp: any = (file as any).processing_progress
    const startedAt = (file as any).processing_at
    const etaAtTop = (file as any).eta_at
    if (!startedAt) return 0
    const startedMs = new Date(startedAt).getTime()
    // Prefer absolute ETA timestamp if available
    const etaIso = etaAtTop || (pp && pp.eta_at)
    if (etaIso) {
      const etaMs = new Date(etaIso).getTime()
      const total = Math.max(1, (etaMs - startedMs) / 1000)
      const elapsed = Math.max(0, (Date.now() - startedMs) / 1000)
      const pct = Math.floor((elapsed / total) * 100)
      return Math.max(0, Math.min(99, pct))
    }
    if (pp && pp.projected_eta && pp.projected_eta > 0) {
      const eta = Number(pp.projected_eta)
      const elapsedSec = Math.max(0, (Date.now() - startedMs) / 1000)
      const pct = Math.floor((elapsedSec / eta) * 100)
      return Math.max(0, Math.min(99, pct))
    }
    return 0
  }

  const getProgressPercentage = () => {
    if (file.status === "UPLOADING" && file.upload_progress) {
      return file.upload_progress.percentage
    }
    if (file.status === "PROCESSING") {
      return computeProcessingPct()
    }
    if (file.status === "COMPLETE" || file.status === "ERROR") {
      return 100
    }
    return 0
  }

  const getUploadProgress = () => {
    return file.upload_progress?.percentage || 0
  }

  const getProcessingProgress = () => {
    if (file.status === "PROCESSING") {
      return computeProcessingPct()
    }
    if (file.status === "COMPLETE" || file.status === "ERROR") {
      return 100
    }
    return 0
  }

  const handleDownload = async () => {
    if (file.status === "ERROR") {
      toast({
        title: "Download unavailable",
        description: "File can't be downloaded due to an error in conversion process.",
        variant: "destructive",
      })
      return
    }

    if (file.status === "UPLOADING") {
      toast({
        title: "Please wait",
        description: "File is currently uploading. Download will be available once conversion completes.",
      })
      return
    }

    if (file.status === "QUEUED") {
      toast({
        title: "Please wait",
        description: "File is queued for processing. Download will be available once conversion completes.",
      })
      return
    }

    if (file.status === "PROCESSING") {
      toast({
        title: "Please wait",
        description: "File is being converted. Download will be available once conversion completes.",
      })
      return
    }

    if (onDownload) {
      await onDownload(file)
    }
  }

  const handleTrashAction = async () => {
    if (context === 'downloads' && file.status === "COMPLETE" && onDelete) {
      console.log("[Downloads] Delete clicked:", file.id, { filename: file.name, status: file.status })
      try {
        await onDelete(file.id)
        toast({
          title: "Deleted",
          description: `${file.name} removed from history.`,
        })
      } catch (e) {
        toast({ title: "Delete failed", variant: "destructive" })
      }
    } else if (file.status === "COMPLETE" && onDismiss) {
      // For completed jobs in queue context, just dismiss from UI without API call
      console.log("[Card] Dismiss clicked (complete)", (file as any).jobId || file.id, { filename: file.name, status: file.status })
      onDismiss(((file as any).jobId || file.id) as string)
      toast({
        title: "Removed",
        description: `${file.name} removed from queue.`,
      })
    } else if ((file.status === "UPLOADING" || file.status === "PROCESSING" || file.status === "QUEUED") && onCancel) {
      console.log("[Card] Cancel clicked:", (file as any).jobId || file.id, { filename: file.name, status: file.status })
      onCancel(((file as any).jobId || file.id) as string)
      toast({
        title: "Cancelled",
        description: `${file.name} has been cancelled.`,
      })
    } else if (file.status === "ERROR" && onCancel) {
      console.log("[Card] Remove clicked (error):", (file as any).jobId || file.id, { filename: file.name, status: file.status })
      onCancel(((file as any).jobId || file.id) as string)
      toast({
        title: "Removed",
        description: `${file.name} removed from queue.`,
      })
    } else if (onDelete) {
      setIsDeleting(true)
      try {
        await onDelete(file.id)
      } finally {
        setIsDeleting(false)
      }
    }
  }

  const getTrashButtonLabel = () => {
    if (file.status === "COMPLETE") return context === 'downloads' ? "Delete" : "Remove"
    if (file.status === "UPLOADING" || file.status === "PROCESSING") return "Cancel"
    if (file.status === "ERROR") return "Remove"
    if (file.status === "QUEUED") return "Cancel"
    return "Cancel"
  }

  const renderStages = () => {
    const isComplete = file.status === "COMPLETE"
    const isError = file.status === "ERROR"
    const isQueued = file.status === "QUEUED"
    const isProcessing = file.status === "PROCESSING"
    const isUploading = file.status === "UPLOADING"
    const uploadNotStarted = isUploading && getUploadProgress() === 0

    // Always show a simple PROCESSING label (no initialising/finalising states)

    return (
      <div className="flex items-center gap-1.5 text-xs">
        {/* UPLOADING */}
        <span
          className={`flex items-center gap-1 ${
            uploadNotStarted
              ? "text-muted-foreground/50"
              : isComplete || isError || isProcessing || isQueued
                ? "text-muted-foreground/50 line-through"
                : statusColors.text
          }`}
        >
          <Upload className={`h-3 w-3 ${isUploading && !uploadNotStarted ? "animate-spin" : ""}`} />
          <span className="hidden md:inline">UPLOADING</span>
        </span>

        <span className="text-muted-foreground">→</span>

        {/* QUEUED or PROCESSING */}
        {isQueued ? (
          <>
            <span className={`flex items-center gap-1 ${statusColors.text}`}>
              <Clock className="h-3 w-3 animate-spin" />
              <span className="hidden md:inline">QUEUED</span>
            </span>
            <span className="text-muted-foreground">→</span>
            <span className="text-muted-foreground/50 flex items-center gap-1">
              <Check className="h-3 w-3" />
              <span className="hidden md:inline">COMPLETE</span>
            </span>
          </>
        ) : (
          <>
            <span
              className={`flex items-center gap-1 ${
                uploadNotStarted
                  ? "text-muted-foreground/50"
                  : isProcessing
                    ? statusColors.text
                    : isComplete || isError
                      ? "text-muted-foreground/50 line-through"
                      : "text-muted-foreground/50"
              }`}
            >
              <Settings className={`h-3 w-3 ${isProcessing ? "animate-spin" : ""}`} />
              <span className="hidden md:inline">PROCESSING</span>
            </span>
            <span className="text-muted-foreground">→</span>
            {isError ? (
              <span className={`flex items-center gap-1 ${statusColors.text}`}>
                <AlertCircle className="h-3 w-3" />
                <span className="hidden md:inline">ERRORRED</span>
              </span>
            ) : (
              <span
                className={
                  uploadNotStarted
                    ? "text-muted-foreground/50 flex items-center gap-1"
                    : isComplete
                      ? `flex items-center gap-1 ${statusColors.text}`
                      : "text-muted-foreground/50 flex items-center gap-1"
                }
              >
                <Check className="h-3 w-3" />
                <span className="hidden md:inline">COMPLETE</span>
              </span>
            )}
          </>
        )}
      </div>
    )
  }

  const progressPercentage = getProgressPercentage()
  const uploadProgress = getUploadProgress()
  const processingProgress = getProcessingProgress()
  const isComplete = file.status === "COMPLETE"
  const isError = file.status === "ERROR"
  const isUploading = file.status === "UPLOADING"
  const isProcessing = file.status === "PROCESSING"
  const isQueued = file.status === "QUEUED"

  return (
    <Card className="overflow-hidden">
      {/* Main content */}
      <div className="p-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4 max-w-full overflow-hidden">
          {/* File icon and name */}
          <div className="flex items-start md:items-center gap-1.5 md:gap-3 min-w-0 flex-1 max-w-full overflow-hidden">
            {showActions && (
              <div className="md:hidden shrink-0 flex items-center">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-10 w-10 text-muted-foreground">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={handleTrashAction} disabled={isDeleting}>
                      <Trash2 className="h-4 w-4 mr-2" />
                      {getTrashButtonLabel()}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}

            <div className="flex items-start md:items-center gap-1.5 md:gap-3 flex-1 min-w-0 max-w-full overflow-hidden">
              {isComplete && showActions ? (
                <Button
                  size="icon"
                  onClick={handleDownload}
                  disabled={isDownloading}
                  className="md:hidden h-10 w-10 shrink-0 bg-success hover:bg-success/90 text-white"
                >
                  <Download className="h-4 w-4" />
                </Button>
              ) : (
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg md:hidden ${statusColors.bg} ${statusColors.text}`}
                >
                  <span className="text-sm font-medium uppercase">{getFileIcon()}</span>
                </div>
              )}

              <div
                className={`hidden md:flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${statusColors.bg} ${statusColors.text}`}
              >
                <span className="text-sm font-medium uppercase">{getFileIcon()}</span>
              </div>

              {/* Filesize inline with filename */}
              <div className="min-w-0 flex-1 max-w-full overflow-hidden">
                <div className="flex items-center gap-2 max-w-full overflow-hidden">
                  <p className="font-medium truncate flex-1 min-w-0">{file.name}</p>
                  {/* Status label */}
                  <span
                    className={`md:hidden text-xs font-medium w-24 max-w-24 text-right shrink-0 ${statusColors.text}`}
                  >
                    {file.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 max-w-full overflow-hidden">
                  <p className="text-sm text-muted-foreground shrink-0 md:hidden">{formatFileSizeMobile(file.size)}</p>
                  {file.device && <p className="text-sm text-muted-foreground truncate md:hidden">{file.device}</p>}
                  <p className="text-sm text-muted-foreground truncate hidden md:block">
                    {formatFileSize(file.size)}
                    {file.device && (
                      <>
                        {" • "}
                        <span className="text-muted-foreground truncate">{file.device}</span>
                      </>
                    )}
                  </p>
                  {/* Status icons and progress bar for mobile view */}
                  <div className="md:hidden flex items-center gap-1.5 shrink-0">
                    <Upload
                      className={`h-3 w-3 ${isUploading && getUploadProgress() > 0 ? "animate-spin" : ""} ${
                        file.status === "UPLOADING" && getUploadProgress() > 0
                          ? statusColors.text
                          : "text-muted-foreground/50"
                      }`}
                    />
                    {isQueued ? (
                      <Clock className={`h-3 w-3 animate-spin ${statusColors.text}`} />
                    ) : (
                      <Settings
                        className={`h-3 w-3 ${isProcessing ? "animate-spin" : ""} ${
                          isProcessing ? statusColors.text : "text-muted-foreground/50"
                        }`}
                      />
                    )}
                    {isError ? (
                      <AlertCircle className={`h-3 w-3 ${statusColors.text}`} />
                    ) : (
                      <Check className={`h-3 w-3 ${isComplete ? statusColors.text : "text-muted-foreground/50"}`} />
                    )}
                    {/* Progress bar for mobile */}
                    <div className="flex items-center gap-1 ml-1 shrink-0">
                      <div className="relative h-1.5 w-12 overflow-hidden rounded-full bg-muted shrink-0">
                        {/* Upload layer (lighter purple) underneath */}
                        <div
                          className="absolute left-0 top-0 h-full bg-[hsl(var(--theme-lightest))] transition-all duration-300"
                          style={{ width: `${uploadProgress}%` }}
                        />
                        {/* Processing layer (darker) on top */}
                        <div
                          className={`absolute left-0 top-0 h-full transition-all duration-300 ${
                            isComplete || isError || isProcessing ? statusColors.progressBar : "bg-transparent"
                          }`}
                          style={{ width: `${processingProgress}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-muted-foreground tabular-nums w-9 text-right shrink-0">
                        {Math.round(progressPercentage)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Status stages and progress - Desktop only */}
              <div className="hidden md:flex md:flex-row md:items-center gap-3 md:gap-4">
                {renderStages()}

                {/* Progress bar */}
                <div className="flex items-center gap-2 min-w-[120px]">
                  <div className="relative h-2 w-full overflow-hidden rounded-full bg-muted">
                    {/* Upload layer (lighter purple) underneath */}
                    <div
                      className="absolute left-0 top-0 h-full bg-[hsl(var(--theme-lightest))] transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                    {/* Processing layer (darker) on top */}
                    <div
                      className={`absolute left-0 top-0 h-full transition-all duration-300 ${
                        isComplete || isError || isProcessing ? statusColors.progressBar : "bg-transparent"
                      }`}
                      style={{ width: `${processingProgress}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-muted-foreground tabular-nums w-10 text-right">
                    {Math.round(progressPercentage)}%
                  </span>
                </div>

                {/* Desktop action buttons */}
                {showActions && (
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={handleDownload}
                      disabled={isDownloading || !(file.status === "COMPLETE" || file.isConverted)}
                      className={`bg-success hover:bg-success/90 text-white ${
                        !(file.status === "COMPLETE" || file.isConverted) ? "invisible" : ""
                      }`}
                    >
                      <Download className="h-4 w-4 mr-1.5" />
                      {isDownloading ? "Downloading..." : "Download"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={handleTrashAction}
                      disabled={isDeleting}
                      className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                      title={getTrashButtonLabel()}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}
