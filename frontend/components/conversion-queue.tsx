"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import {
  Loader2,
  FileText,
  AlertTriangle,
  X,
  Download,
  XCircle,
  Settings,
  Upload,
  Cog,
  CheckCircle2,
  AlertCircle,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { motion } from "framer-motion"
import { useState, useEffect, useRef, useCallback } from "react"
import type { PendingUpload, AdvancedOptionsType } from "./manga-converter"
import { fetchWithLicense } from "@/lib/utils"
import { log, logError } from "@/lib/logger"
import { toast } from "sonner"
// Removed Tooltip usage on queue action buttons to avoid ref update loop

interface ConversionQueueProps {
  pendingUploads: PendingUpload[]
  isConverting: boolean
  onConvert: () => void
  onCancelJob?: (file: PendingUpload) => void
  selectedProfile: string
  globalAdvancedOptions?: AdvancedOptionsType
  onReorder?: (newOrder: PendingUpload[]) => void
  showAsUploadedFiles?: boolean
  onRemoveFile?: (file: PendingUpload) => void
  onDismissJob?: (file: PendingUpload) => void
  dismissingJobs?: Set<string>
  cancellingJobs?: Set<string>
  isUploaded?: boolean
  currentStatus?: string
  deviceProfiles?: Record<string, string>
  onAddMoreFiles?: () => void
  onNeedsConfiguration?: () => void
  onOpenSidebar?: () => void
  onStartConversion?: () => void
  isReadyToConvert?: () => boolean
}

export function ConversionQueue({
  pendingUploads,
  isConverting,
  onConvert,
  onCancelJob,
  dismissingJobs = new Set(),
  cancellingJobs = new Set(),
  selectedProfile,
  globalAdvancedOptions,
  onReorder,
  showAsUploadedFiles = false,
  onRemoveFile,
  onDismissJob,
  isUploaded = false,
  currentStatus,
  deviceProfiles = {},
  onAddMoreFiles,
  onNeedsConfiguration,
  onOpenSidebar,
  onStartConversion,
  isReadyToConvert,
}: ConversionQueueProps) {
  // Items are now directly used from pendingUploads prop instead of maintaining duplicate state
  const items = pendingUploads

  // Render tooltips only after mount to avoid dev ref/hydration loops
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    setMounted(true)
  }, [])

  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({})
  const [jobUploadEtas, setJobUploadEtas] = useState<Map<string, number>>(new Map())
  const [jobUploadSpeeds, setJobUploadSpeeds] = useState<Map<string, number>>(new Map())
  const [jobSpeedHistories, setJobSpeedHistories] = useState<Map<string, number[]>>(new Map())
  const [jobLastSpeedEmit, setJobLastSpeedEmit] = useState<Map<string, number>>(new Map())
  const [jobUploadStartTimes, setJobUploadStartTimes] = useState<Map<string, number>>(new Map())
  const [jobLastUploadProgress, setJobLastUploadProgress] = useState<Map<string, number>>(new Map())
  const [jobLastUploadTime, setJobLastUploadTime] = useState<Map<string, number>>(new Map())
  // PROCESSING ETA comes from backend; no local countdown
  const [uploadEta, setUploadEta] = useState<number | undefined>(undefined)
  const [displayedUploadRemainingSec, setDisplayedUploadRemainingSec] = useState<number | null>(null)
  const [lastUploadProgress, setLastUploadProgress] = useState<number>(0)
  const [lastUploadTime, setLastUploadTime] = useState<number>(Date.now())
  const [uploadSpeed, setUploadSpeed] = useState<number>(0) // bytes per second
  const [uploadStartTime, setUploadStartTime] = useState<number>(0)
  const [lastEtaUpdateTime, setLastEtaUpdateTime] = useState<number>(0)
  const [speedSampleCount, setSpeedSampleCount] = useState<number>(0)
  const uploadJobIdRef = useRef<string>("unknown")
  const lastLoggedUploadRemainingRef = useRef<number | null>(null)

  const SPEED_EMIT_INTERVAL_MS = 5000
  const SPEED_MEDIAN_WINDOW = Number.parseInt(process.env.NEXT_PUBLIC_UPLOAD_SPEED_WINDOW || "8", 10)
  const median = (arr: number[]) => {
    if (arr.length === 0) return 0
    const sorted = [...arr].sort((a, b) => a - b)
    const mid = Math.floor(sorted.length / 2)
    return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid]
  }

  // Client-side PROCESSING<bos> ticker (based on backend-provided ETA at start)
  const [processingStartTime, setProcessingStartTime] = useState<number | null>(null)
  const [processingEtaSec, setProcessingEtaSec] = useState<number | null>(null)
  const [clientProcessingProgress, setClientProcessingProgress] = useState<number>(0)
  const [displayedRemainingSec, setDisplayedRemainingSec] = useState<number | null>(null)
  // Logging refs for 10% progress steps and ETA second decrements
  const lastLoggedProcessingTenthRef = useRef<number | null>(null)
  const lastLoggedRemainingSecRef = useRef<number | null>(null)
  const processingJobIdRef = useRef<string>("unknown")

  // Refs to track last logged progress percentage for each job stage (to log only at 10% intervals)
  // No queued/progress logs: handled by backend

  // Removed useEffect for items state synchronization:
  // useEffect(() => {
  //   if (JSON.stringify(items) !== JSON.stringify(pendingUploads)) {
  //     setItems(pendingUploads)
  //   }
  // }, [pendingUploads])

  // No QUEUED ETA: we intentionally do not compute or display ETA while QUEUED

  // No local remaining time state; rely on backend

  // No QUEUED countdown: progress remains at 0% until PROCESSING

  // No PROCESSING countdown; backend provides remaining_seconds

  // Initialize client-side PROCESSING tickers when backend ETA is available
  useEffect(() => {
    const processingFile = pendingUploads.find((f) => f.status === "PROCESSING" && f.processing_progress)
    const pp = processingFile?.processing_progress
    if (pp?.projected_eta && pp.projected_eta > 0) {
      // Initialize only once per processing phase to avoid Date.now()-driven loops
      if (processingStartTime == null) {
        const baseElapsed = pp.elapsed_seconds ?? 0
        const startMs = Date.now() - baseElapsed * 1000
        setProcessingStartTime(startMs)
        setProcessingEtaSec(pp.projected_eta)
        // Start from backend-progress if provided
        const initialProgress =
          pp.progress_percent != null
            ? Math.floor(Math.max(0, Math.min(99, pp.progress_percent)))
            : Math.floor(Math.max(0, Math.min(99, (baseElapsed / pp.projected_eta) * 100)))
        setClientProcessingProgress(initialProgress)
        const initialRemaining =
          pp.remaining_seconds != null ? pp.remaining_seconds : Math.max(0, Math.ceil(pp.projected_eta - baseElapsed))
        setDisplayedRemainingSec(initialRemaining)
        // Track job id for logging
        const jId = (processingFile as any)?.jobId || (processingFile as any)?.job_id
        processingJobIdRef.current = jId || "unknown"
        // Reset logging refs when (re)initializing ticker
        lastLoggedProcessingTenthRef.current = null
        lastLoggedRemainingSecRef.current = null
      }
    } else {
      setProcessingStartTime(null)
      setProcessingEtaSec(null)
      setClientProcessingProgress(0)
      setDisplayedRemainingSec(null)
      processingJobIdRef.current = "unknown"
      lastLoggedProcessingTenthRef.current = null
      lastLoggedRemainingSecRef.current = null
    }
  }, [pendingUploads, processingStartTime])

  // Progress ticker: update smoothly every 100ms for smooth animation
  useEffect(() => {
    if (processingStartTime && processingEtaSec && processingEtaSec > 0) {
      const interval = setInterval(() => {
        const elapsed = (Date.now() - processingStartTime) / 1000
        const progress = (elapsed / processingEtaSec) * 100 // Keep fractional for smooth rendering
        const next = Math.max(0, Math.min(99, progress))
        setClientProcessingProgress((prev) => {
          const value = Math.max(prev, next)
          // Log on every 10% boundary crossed (10,20,...,90)
          const currentTenth = Math.floor(value / 10) * 10
          const lastTenth = lastLoggedProcessingTenthRef.current ?? -1
          if (value > 0 && currentTenth !== lastTenth && currentTenth >= 10 && currentTenth <= 90) {
            lastLoggedProcessingTenthRef.current = currentTenth
            const jobId = processingJobIdRef.current
            const remaining = displayedRemainingSec ?? Math.max(0, Math.ceil(processingEtaSec - elapsed))
            log(`[UI] Converting progress (ticker): ${currentTenth}%`, {
              progress_percent: currentTenth,
              elapsed_seconds: Math.floor(elapsed),
              remaining_seconds: Math.floor(remaining),
              projected_eta: processingEtaSec,
              job_id: jobId,
            })
          }
          return value
        })
      }, 100) // Update every 100ms for smooth animation
      return () => clearInterval(interval)
    }
  }, [processingStartTime, processingEtaSec])

  // Remaining time ticker: decrement 1s each second
  useEffect(() => {
    if (processingStartTime) {
      const interval = setInterval(() => {
        setDisplayedRemainingSec((prev) => {
          if (prev == null) return prev
          const next = Math.max(0, prev - 1)
          // Log each second decremented
          const last = lastLoggedRemainingSecRef.current
          if (last == null || next !== last) {
            lastLoggedRemainingSecRef.current = next
            const jobId = processingJobIdRef.current
            log(`[UI] ETA tick: ${next}s remaining`, {
              remaining_seconds: next,
              job_id: jobId,
            })
          }
          return next
        })
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [processingStartTime])

  // Reset when status changes
  useEffect(() => {
    if (currentStatus === "COMPLETE") {
      setUploadEta(undefined)
      setLastUploadProgress(0)
    }

    // Reset PROCESSING-specific state when leaving PROCESSING
    // No PROCESSING-specific local state to reset

    // No QUEUED-specific state to reset

    // Reset UPLOADING-specific state when leaving UPLOADING
    if (currentStatus !== "UPLOADING") {
      setUploadEta(undefined)
      setLastUploadProgress(0)
      setLastUploadTime(Date.now())
      setSpeedSampleCount(0)
    }
  }, [currentStatus])

  // Calculate upload ETA based on real-time upload speed (bytes per second)
  useEffect(() => {
    // Check both global status and per-file status
    const uploadingFile = pendingUploads.find((f) => f.status === "UPLOADING")
    const isUploading = currentStatus === "UPLOADING" || uploadingFile !== undefined

    if (
      isUploading &&
      uploadingFile?.upload_progress?.percentage !== undefined &&
      uploadingFile?.upload_progress?.percentage >= 0
    ) {
      const now = Date.now()
      const jobId = uploadingFile.jobId || uploadingFile.job_id || "unknown"
      const fileSize = uploadingFile.size
      const uploadedBytes =
        uploadingFile.upload_progress.uploaded_bytes || (uploadingFile.upload_progress.percentage / 100) * fileSize
      const currentProgress = uploadingFile.upload_progress.percentage

      // Initialize upload start time and progress tracking for this job
      if (!jobUploadStartTimes.has(jobId) || jobUploadStartTimes.get(jobId) === 0) {
        setJobUploadStartTimes((prev) => new Map(prev).set(jobId, now))
        setJobLastUploadProgress((prev) => new Map(prev).set(jobId, currentProgress))
        setJobLastUploadTime((prev) => new Map(prev).set(jobId, now))
        // Resetting global trackers too for consistency if this is the primary uploader
        if (uploadingFile === pendingUploads[0]) {
          setUploadStartTime(now)
          setLastUploadProgress(currentProgress)
          setLastUploadTime(now)
          setSpeedSampleCount(0)
        }
        return
      }

      const lastProgress = jobLastUploadProgress.get(jobId) || 0
      const lastTime = jobLastUploadTime.get(jobId) || now
      const progressDelta = currentProgress - lastProgress
      const timeDelta = (now - lastTime) / 1000 // Convert to seconds

      // Only update if we have meaningful progress (avoid noise from rapid updates)
      if (progressDelta > 0.1 && timeDelta > 0.2) {
        // Calculate instantaneous speed (bytes uploaded in this interval / time elapsed)
        const bytesDelta = uploadedBytes - (lastProgress / 100) * fileSize
        const instantSpeed = bytesDelta / timeDelta

        // Use job-specific speed, fallback to global if necessary
        // Accumulate instantaneous speed measurements for median calculation
        setJobSpeedHistories((prev) => {
          const next = new Map(prev)
          const arr = next.get(jobId) ? [...(next.get(jobId) as number[])] : []
          arr.push(instantSpeed)
          while (arr.length > SPEED_MEDIAN_WINDOW) arr.shift()
          next.set(jobId, arr)
          return next
        })
        setJobLastUploadProgress((prev) => new Map(prev).set(jobId, currentProgress))
        setJobLastUploadTime((prev) => new Map(prev).set(jobId, now))

        // Also update global trackers if this is the primary uploader
        if (uploadingFile === pendingUploads[0]) {
          // Keep a rough instantaneous reading internally; UI uses median/5s cadence
          setUploadSpeed(instantSpeed)
          setLastUploadProgress(currentProgress)
          setLastUploadTime(now)
          setSpeedSampleCount((prev) => prev + 1)
        }

        // Speed and ETA publication handled by 5s cadence below
      }
    } else if (!isUploading) {
      // Reset upload tracking when not uploading
      setUploadStartTime(0)
      setUploadSpeed(0)
      setUploadEta(undefined)
      setDisplayedUploadRemainingSec(null)
      setSpeedSampleCount(0)
      setJobUploadEtas(new Map())
      setJobUploadSpeeds(new Map())
      setJobUploadStartTimes(new Map())
      setJobLastUploadProgress(new Map())
      setJobLastUploadTime(new Map())
    }
  }, [pendingUploads, currentStatus])

  // Keep displayed upload ETA in sync when a fresh estimate arrives
  useEffect(() => {
    if (uploadEta && uploadEta > 0) {
      setDisplayedUploadRemainingSec(uploadEta)
    }
  }, [uploadEta])

  // Progressive upload ETA countdown (decrement by 1s each second)
  useEffect(() => {
    const uploadingFile = pendingUploads.find((f) => f.status === "UPLOADING")
    const isUploading = currentStatus === "UPLOADING" || uploadingFile !== undefined
    if (isUploading && displayedUploadRemainingSec != null) {
      const interval = setInterval(() => {
        setDisplayedUploadRemainingSec((prev) => {
          if (prev == null) return prev
          const next = Math.max(0, prev - 1)
          // Log each decrement
          if (lastLoggedUploadRemainingRef.current == null || next !== lastLoggedUploadRemainingRef.current) {
            lastLoggedUploadRemainingRef.current = next
            const jobId = uploadJobIdRef.current // Use global ref for now
            log(`[UI] Upload ETA tick: ${next}s remaining`, {
              remaining_seconds: next,
              job_id: jobId,
            })
          }
          return next
        })
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [currentStatus, pendingUploads])

  useEffect(() => {
    const now = Date.now()

    pendingUploads.forEach((file) => {
      const jobId = file.jobId || ""
      const uploadProgress = file.upload_progress?.percentage || 0
      const uploadProgressConfirmed = (file.upload_progress as any)?.confirmed_percentage || uploadProgress
      const eta = jobUploadEtas.get(jobId)
      const speed = jobUploadSpeeds.get(jobId) || 0

      // Initialize tracking for new uploads
      if (uploadProgress === 0 && !jobUploadStartTimes.has(jobId)) {
        setJobUploadStartTimes((prev) => new Map(prev).set(jobId, now))
        setJobLastUploadProgress((prev) => new Map(prev).set(jobId, 0))
        setJobLastUploadTime((prev) => new Map(prev).set(jobId, now))
        setJobLastSpeedEmit((prev) => new Map(prev).set(jobId, 0))
        setJobSpeedHistories((prev) => new Map(prev).set(jobId, []))
        return
      }

      // Calculate instantaneous speed when progress changes
      const lastProgress = jobLastUploadProgress.get(jobId) || 0
      const lastTime = jobLastUploadTime.get(jobId) || now

      if (uploadProgress > lastProgress && uploadProgress < 100) {
        const timeDiff = (now - lastTime) / 1000 // seconds
        const progressDiff = uploadProgress - lastProgress

        if (timeDiff > 0 && progressDiff > 0) {
          const totalBytes = file.size // Total size of the file
          const uploadedBytes = (progressDiff / 100) * totalBytes // Bytes uploaded in this interval
          const instSpeed = uploadedBytes / timeDiff

          // Append sample to history
          setJobSpeedHistories((prev) => {
            const next = new Map(prev)
            const arr = next.get(jobId) ? [...(next.get(jobId) as number[])] : []
            arr.push(instSpeed)
            while (arr.length > SPEED_MEDIAN_WINDOW) arr.shift()
            next.set(jobId, arr)
            return next
          })

          // Update last progress/time
          setJobLastUploadProgress((prev) => new Map(prev).set(jobId, uploadProgress))
          setJobLastUploadTime((prev) => new Map(prev).set(jobId, now))

          // Publish every 5s using median of recent samples
          const lastEmit = jobLastSpeedEmit.get(jobId) || 0
          if (now - lastEmit >= SPEED_EMIT_INTERVAL_MS) {
            const hist = jobSpeedHistories.get(jobId) || []
            const med = median(hist)
            setJobUploadSpeeds((prev) => new Map(prev).set(jobId, med))

            const remainingBytes = totalBytes - uploadedBytes
            const etaSeconds = med > 0 ? remainingBytes / med : 0
            if (etaSeconds > 0 && etaSeconds < 3600) {
              setJobUploadEtas((prev) => new Map(prev).set(jobId, Math.ceil(etaSeconds)))
            }

            setJobLastSpeedEmit((prev) => new Map(prev).set(jobId, now))

            // Persist latest median upload speed for dynamic part sizing in future uploads
            try {
              if (med > 0) {
                localStorage.setItem("upload_speed_bps", String(Math.floor(med)))
              }
            } catch {}
          }
        }
      }
    })
  }, [pendingUploads, jobLastSpeedEmit, jobSpeedHistories])

  const getJobUploadInfo = useCallback(
    (file: PendingUpload) => {
      const jobId = file.jobId || ""
      const uploadProgress = file.upload_progress?.percentage || 0
      const uploadProgressConfirmed = (file.upload_progress as any)?.confirmed_percentage || uploadProgress
      const eta = jobUploadEtas.get(jobId)
      const speed = jobUploadSpeeds.get(jobId) || 0

      return {
        uploadProgress,
        uploadProgressConfirmed,
        eta,
        speed,
      }
    },
    [jobUploadEtas, jobUploadSpeeds],
  )

  const isJobRunning = (file: PendingUpload) => {
    return file.status === "UPLOADING" || file.status === "QUEUED" || file.status === "PROCESSING"
  }

  const hasActiveJobs = () => {
    return pendingUploads.some((file) => isJobRunning(file))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const formatUploadSpeed = (bytesPerSecond: number) => {
    if (bytesPerSecond === 0) return "0 B/s"
    const k = 1024
    const sizes = ["B/s", "KB/s", "MB/s", "GB/s"]
    const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k))
    return Number.parseFloat((bytesPerSecond / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      // Ensure we never show less than 1s
      const displaySeconds = Math.max(1, Math.round(seconds))
      return `${displaySeconds}s`
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = Math.round(seconds % 60)
      // If we have remaining seconds, ensure they're at least 1
      if (remainingSeconds > 0) {
        const displaySeconds = Math.max(1, remainingSeconds)
        return `${minutes}m ${displaySeconds}s`
      }
      return `${minutes}m`
    } else {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`
    }
  }

  const getStatusBadge = (file: PendingUpload, index: number) => {
    if (file.isConverted) {
      return (
        <Badge
          variant="secondary"
          className="uppercase text-xs font-medium bg-success/10 text-green-600 dark:text-green-400 border-success/20"
        >
          Complete
        </Badge>
      )
    }

    if (file.error) {
      return (
        <Badge variant="destructive" className="uppercase text-xs font-medium">
          Error
        </Badge>
      )
    }

    if (selectedProfile === "Placeholder" && !isConverting && !file.status) {
      return (
        <Badge
          variant="secondary"
          className="uppercase text-xs font-medium bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
        >
          Needs Configuring
        </Badge>
      )
    }

    // Check file's own status property first (from session update)
    if (file.status) {
      switch (file.status) {
        case "UPLOADING":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-400/10 text-red-500 dark:text-red-400 border-red-400/20"
            >
              Uploading
            </Badge>
          )
        case "QUEUED":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-500/10 text-red-600 dark:text-red-500 border-red-500/20"
            >
              Queued
            </Badge>
          )
        case "PROCESSING":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-600/10 text-red-700 dark:text-red-600 border-red-600/20"
            >
              Converting
            </Badge>
          )
        case "COMPLETE":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-700/10 text-red-800 dark:text-red-700 border-red-700/20"
            >
              Finished
            </Badge>
          )
        default:
          break
      }
    }

    // Fallback to global status for first item when converting
    if (isConverting && index === 0 && currentStatus) {
      switch (currentStatus) {
        case "UPLOADING":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-400/10 text-red-500 dark:text-red-400 border-red-400/20"
            >
              Uploading
            </Badge>
          )
        case "QUEUED":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-500/10 text-red-600 dark:text-red-500 border-red-500/20"
            >
              Converting
            </Badge>
          )
        case "PROCESSING":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-600/10 text-red-700 dark:text-red-600 border-red-600/20"
            >
              Converting
            </Badge>
          )
        case "COMPLETE":
          return (
            <Badge
              variant="secondary"
              className="uppercase text-xs font-medium bg-red-700/10 text-red-800 dark:text-red-700 border-red-700/20"
            >
              Finished
            </Badge>
          )
        default:
          return (
            <Badge variant="secondary" className="uppercase text-xs font-medium">
              Waiting
            </Badge>
          )
      }
    }

    // Default: show "Ready" for files waiting to start
    return (
      <Badge variant="secondary" className="uppercase text-xs font-medium bg-muted">
        Ready
      </Badge>
    )
  }

  // Timeline stage calculation
  const getTimelineStage = (file: PendingUpload, index: number) => {
    const status = file.status

    // Handle error state - show as stage 3 but mark as errored
    if (file.error) {
      return { stage: 3, progress: 100, label: "Error", eta: null, isError: true }
    }

    // Before conversion starts - stage -1 means no active stage yet
    if (!status) return { stage: -1, progress: 0, label: "Ready", eta: null, isError: false }

    if (status === "QUEUED") {
      // WebSocket emits QUEUED after upload completes and before processing
      // Show as queued without progress - worker will pick it up when ready
      return {
        stage: 0.5, // queued at converting position
        progress: 0, // No progress shown during queue wait
        label: "Queued",
        eta: null,
        isError: false,
      }
    }

    // Stage 0: Uploading (0-100% of upload)
    if (status === "UPLOADING") {
      // Priority: Use global uploadProgress (real-time from frontend) over backend's file.upload_progress
      // The backend's percentage is based on completed parts only, which lags behind actual upload progress
      const uploadPct = file.upload_progress?.percentage || 0 // Use per-file upload progress
      const safeUploadPct = Math.min(100, uploadPct) // Only enforce maximum, allow 0%
      let label = `Uploading - ${Math.round(safeUploadPct)}%`
      const currentJobSpeed = jobUploadSpeeds.get(file.jobId || file.job_id || "") || 0
      if (currentJobSpeed > 0) {
        label += ` (@${formatUploadSpeed(currentJobSpeed)})`
      }
      const currentJobEta = jobUploadEtas.get(file.jobId || file.job_id || "")
      return {
        stage: 0,
        progress: safeUploadPct,
        label,
        eta: currentJobEta ?? null,
        isError: false,
      }
    }

    // Stage 1: Converting
    if (status === "PROCESSING") {
      // Check if this file is the one currently being processed with active ticker
      const isActiveProcessingFile = file.processing_progress && processingStartTime && processingEtaSec

      // Use client-side ticker if available (continuous updates)
      if (isActiveProcessingFile) {
        return {
          stage: 1,
          progress: Math.max(0, Math.min(99, clientProcessingProgress)),
          label: "Converting",
          eta: displayedRemainingSec ?? null,
          isError: false,
        }
      }
      // Fallback to backend-provided processing_progress if ticker not initialized
      if (file.processing_progress) {
        const { progress_percent, remaining_seconds } = file.processing_progress
        const safeProgress = Math.max(0, Math.min(99, progress_percent || 0))
        return {
          stage: 1,
          progress: safeProgress,
          label: "Converting",
          eta: remaining_seconds ?? null,
          isError: false,
        }
      }
      return { stage: 1, progress: 0, label: "Converting", eta: null, isError: false }
    }

    if (status === "COMPLETE") {
      return { stage: 2, progress: 100, label: "Ready for Download", eta: null, isError: false }
    }

    return { stage: -1, progress: 0, label: "Ready", eta: null, isError: false }
  }

  const getStageColors = (stageIndex: number) => {
    switch (stageIndex) {
      case 0: // Upload - lightest
        return {
          light: "bg-theme-lightest/40",
          dark: "bg-theme-lightest",
          icon: "text-theme-light",
          border: "border-theme-lightest",
          bg: "bg-theme-lightest",
        }
      case 1: // Converting - light (was medium, now light since we removed Reading stage)
        return {
          light: "bg-theme-light/40",
          dark: "bg-theme-light",
          icon: "text-theme-medium",
          border: "border-theme-light",
          bg: "bg-theme-light",
        }
      case 2: // Complete - medium (was dark, now medium since we removed Reading stage)
        return {
          light: "bg-theme-medium/40",
          dark: "bg-theme-medium",
          icon: "text-theme-dark",
          border: "border-theme-medium",
          bg: "bg-theme-medium",
        }
      default:
        return {
          light: "bg-muted",
          dark: "bg-primary",
          icon: "text-muted-foreground",
          border: "border-muted",
          bg: "bg-muted",
        }
    }
  }

  const renderTimeline = (file: PendingUpload, index: number, actionButtons?: React.ReactNode) => {
    const { stage, progress, label, eta, isError } = getTimelineStage(file, index)

    const stages = [
      { icon: Upload, label: "Upload", shortLabel: "Upload", active: stage >= 0 },
      { icon: Cog, label: "Converting", shortLabel: "Convert", active: stage >= 1 },
      {
        icon: isError ? AlertCircle : CheckCircle2,
        label: isError ? "Error" : "Complete",
        shortLabel: isError ? "Error" : "Done",
        active: stage >= 2,
      },
    ]

    const isQueuedAtUpload = stage === -0.5
    const isQueuedAtConverting = stage === 0.5
    const isQueued = isQueuedAtUpload || isQueuedAtConverting

    const displayStage = isQueuedAtUpload ? 0 : isQueuedAtConverting ? 1 : stage
    const showProgressBar = !isQueued && displayStage >= 0 && displayStage < stages.length

    // Each stage shows its own 100% progress bar when active
    const currentStageProgress = displayStage >= 0 && displayStage < stages.length ? progress : 0
    const isCompleted = displayStage >= stages.length - 1 && !isError
    const isErrored = displayStage >= stages.length - 1 && isError

    return (
      <div className="w-full">
        <div className="block sm:hidden space-y-3">
          {/* Stage nodes with connector line */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="relative flex items-start justify-between">
                {/* Background connector line */}
                <div
                  className="absolute h-0.5 bg-muted top-4"
                  style={{
                    left: "16px" /* half of node width (32px / 2) */,
                    right: "16px",
                  }}
                />

                {/* Stage nodes */}
                {stages.map((s, i) => {
                  const Icon = s.icon
                  const isCurrentStage = i === displayStage && displayStage < stages.length - 1
                  const isPastStage =
                    isQueuedAtConverting && i === 0 ? true : displayStage >= stages.length - 1 ? true : i < displayStage
                  const isFutureStage = i > displayStage && displayStage < stages.length - 1
                  const colors = getStageColors(i)

                  const iconClass = `h-4 w-4 ${isCurrentStage && !isQueued ? "animate-pulse" : ""} ${isQueued && i === displayStage ? "animate-spin" : ""}`

                  return (
                    <div key={i} className="flex flex-col items-center">
                      {/* Icon container */}
                      <div
                        className={`
                          relative z-10 flex items-center justify-center
                          w-8 h-8 rounded-full border-2 transition-all duration-300
                          ${
                            isCurrentStage || (isQueued && i === displayStage)
                              ? `${colors.border} ${colors.bg} text-white shadow-md`
                              : isPastStage && isError && i === stages.length - 1
                                ? "border-destructive bg-destructive text-destructive-foreground"
                                : isPastStage
                                  ? `${colors.border} ${colors.bg}/10 ${colors.icon}`
                                  : "border-muted bg-background text-muted-foreground"
                          }
                        `}
                      >
                        {isPastStage && i < stages.length - 1 ? (
                          <CheckCircle2 className="h-4 w-4" />
                        ) : (
                          <Icon className={iconClass} />
                        )}
                      </div>

                      {/* Label */}
                      <div className="mt-1.5 text-center">
                        <span
                          className={`
                            text-[10px] font-medium transition-colors block
                            ${isCurrentStage || (isQueued && i === displayStage) ? "text-foreground" : "text-muted-foreground"}
                            ${displayStage >= stages.length - 1 ? "line-through opacity-60" : isPastStage && i < displayStage ? "line-through opacity-60" : ""}
                          `}
                        >
                          {isQueued && i === displayStage ? "Queued" : s.shortLabel}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Action button on right */}
            {actionButtons && <div className="flex-shrink-0 ml-2">{actionButtons}</div>}
          </div>

          {showProgressBar && (
            <div className="space-y-2">
              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                {Array.from({ length: displayStage }).map((_, i) => (
                  <div
                    key={`completed-stage-${i}`}
                    className={`absolute inset-y-0 left-0 ${getStageColors(i).dark} opacity-60 rounded-full`}
                    style={{ width: "100%" }}
                  />
                ))}

                {/* Current stage progress bar */}
                {displayStage === 0 && file.status === "UPLOADING" ? (
                  <>
                    {/* Light layer: total sent */}
                    <div
                      className={`absolute inset-y-0 left-0 ${getStageColors(0).light} rounded-full transition-all duration-300`}
                      style={{ width: `${Math.min(100, currentStageProgress)}%` }}
                    />
                    {/* Dark layer: confirmed received */}
                    {(() => {
                      const confirmed =
                        (file.upload_progress as any)?.confirmed_percentage ?? file.upload_progress?.percentage
                      return confirmed !== undefined && confirmed > 0 ? (
                        <div
                          className={`absolute inset-y-0 left-0 ${getStageColors(0).dark} rounded-full transition-all duration-300`}
                          style={{ width: `${Math.min(100, confirmed)}%` }}
                        />
                      ) : null
                    })()}
                  </>
                ) : (
                  <div
                    className={`absolute inset-y-0 left-0 ${displayStage === 1 ? getStageColors(2).dark : getStageColors(displayStage).dark} rounded-full transition-all duration-500 ease-out`}
                    style={{ width: `${Math.min(100, currentStageProgress)}%` }}
                  />
                )}
              </div>

              {/* Progress text */}
              <div className="flex items-center justify-between text-[11px] text-muted-foreground px-1">
                {displayStage === 0 && file.status === "UPLOADING" ? (
                  <>
                    <span>
                      Sent: {Math.round(currentStageProgress)}%{(() => {
                        const confirmed =
                          (file.upload_progress as any)?.confirmed_percentage ?? file.upload_progress?.percentage
                        return confirmed !== undefined && confirmed > 0 ? (
                          <span className="ml-1.5 text-primary hidden xs:inline">
                            · Confirmed: {Math.round(confirmed)}%
                          </span>
                        ) : null
                      })()}
                    </span>
                    {(() => {
                      const speed = jobUploadSpeeds.get(file.jobId || file.job_id || "") ?? 0
                      return speed > 0 ? <span className="hidden xs:inline">{formatUploadSpeed(speed)}</span> : null
                    })()}
                  </>
                ) : (
                  <>
                    <span>
                      {Math.round(currentStageProgress)}% {stages[displayStage]?.label || ""}
                    </span>
                    {eta != null && eta > 0 && <span>{formatTime(eta)}</span>}
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Desktop timeline */}
        <div className="hidden sm:block">
          <div className="flex items-start gap-4">
            {/* Timeline stages */}
            <div className="flex-1">
              {/* Stage nodes container with relative positioning for connector */}
              <div className="relative flex items-start justify-between">
                {/* Background connector line - spans between first and last node centers */}
                <div
                  className="absolute h-0.5 bg-muted top-5"
                  style={{
                    left: "20px" /* half of node width (40px / 2) */,
                    right: "20px" /* half of node width */,
                  }}
                />

                {/* Stage nodes */}
                {stages.map((s, i) => {
                  const Icon = s.icon
                  const isCurrentStage = i === displayStage && displayStage < stages.length - 1
                  const isPastStage =
                    isQueuedAtConverting && i === 0 ? true : displayStage >= stages.length - 1 ? true : i < displayStage
                  const isFutureStage = i > displayStage && displayStage < stages.length - 1
                  const colors = getStageColors(i)

                  const iconClass = `h-5 w-5 ${isCurrentStage && !isQueued ? "animate-pulse" : ""} ${isQueued && i === displayStage ? "animate-spin" : ""}`

                  return (
                    <div key={i} className="flex flex-col items-center">
                      {/* Icon container */}
                      <div
                        className={`
                          relative z-10 flex items-center justify-center
                          w-10 h-10 rounded-full border-2 transition-all duration-300
                          ${
                            isCurrentStage || (isQueued && i === displayStage)
                              ? `${colors.border} ${colors.bg} text-white shadow-md`
                              : isPastStage && isError && i === stages.length - 1
                                ? "border-destructive bg-destructive text-destructive-foreground"
                                : isPastStage
                                  ? `${colors.border} ${colors.bg}/10 ${colors.icon}`
                                  : "border-muted bg-background text-muted-foreground"
                          }
                        `}
                      >
                        {isPastStage && i < stages.length - 1 ? (
                          <CheckCircle2 className="h-5 w-5" />
                        ) : (
                          <Icon className={iconClass} />
                        )}
                      </div>

                      {/* Label */}
                      <div className="mt-2 text-center">
                        <span
                          className={`
                            text-xs font-medium transition-colors block
                            ${isCurrentStage || (isQueued && i === displayStage) ? "text-foreground" : "text-muted-foreground"}
                            ${displayStage >= stages.length - 1 ? "line-through opacity-60" : isPastStage && i < displayStage ? "line-through opacity-60" : ""}
                          `}
                        >
                          {isQueued && i === displayStage ? "Queued" : s.label}
                        </span>

                        {isCurrentStage && !isQueued && (
                          <div className="text-[10px] text-muted-foreground mt-0.5">
                            {Math.round(currentStageProgress)}%
                            {eta != null && eta > 0 && <span className="hidden md:inline"> · {formatTime(eta)}</span>}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>

              {showProgressBar && (
                <div className="mt-4 space-y-2">
                  <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                    {Array.from({ length: displayStage }).map((_, i) => (
                      <div
                        key={`completed-stage-${i}`}
                        className={`absolute inset-y-0 left-0 ${getStageColors(i).dark} opacity-60 rounded-full`}
                        style={{ width: "100%" }}
                      />
                    ))}

                    {/* Current stage progress bar */}
                    {displayStage === 0 && file.status === "UPLOADING" ? (
                      <>
                        {/* Light layer: total sent */}
                        <div
                          className={`absolute inset-y-0 left-0 ${getStageColors(0).light} rounded-full transition-all duration-300`}
                          style={{ width: `${Math.min(100, currentStageProgress)}%` }}
                        />
                        {/* Dark layer: confirmed received */}
                        {(() => {
                          const confirmed =
                            (file.upload_progress as any)?.confirmed_percentage ?? file.upload_progress?.percentage
                          return confirmed !== undefined && confirmed > 0 ? (
                            <div
                              className={`absolute inset-y-0 left-0 ${getStageColors(0).dark} rounded-full transition-all duration-300`}
                              style={{ width: `${Math.min(100, confirmed)}%` }}
                            />
                          ) : null
                        })()}
                      </>
                    ) : (
                      <div
                        className={`absolute inset-y-0 left-0 ${displayStage === 1 ? getStageColors(2).dark : getStageColors(displayStage).dark} rounded-full transition-all duration-500 ease-out`}
                        style={{ width: `${Math.min(100, currentStageProgress)}%` }}
                      />
                    )}
                  </div>

                  {/* Progress text */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
                    {displayStage === 0 && file.status === "UPLOADING" ? (
                      <>
                        <span>
                          Sent: {Math.round(currentStageProgress)}%{(() => {
                            const confirmed =
                              (file.upload_progress as any)?.confirmed_percentage ?? file.upload_progress?.percentage
                            return confirmed !== undefined && confirmed > 0 ? (
                              <span className="ml-1.5 text-primary hidden xs:inline">
                                · Confirmed: {Math.round(confirmed)}%
                              </span>
                            ) : null
                          })()}
                        </span>
                        {(() => {
                          const speed = jobUploadSpeeds.get(file.jobId || file.job_id || "") ?? 0
                          return speed > 0 ? <span className="hidden xs:inline">{formatUploadSpeed(speed)}</span> : null
                        })()}
                      </>
                    ) : (
                      <>
                        <span>
                          {Math.round(currentStageProgress)}% {stages[displayStage]?.label || ""}
                        </span>
                        {eta != null && eta > 0 && <span>{formatTime(eta)}</span>}
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Action button on right */}
            {actionButtons && <div className="flex-shrink-0">{actionButtons}</div>}
          </div>
        </div>
      </div>
    )
  }

  const getProgressInfo = (file: PendingUpload, index: number) => {
    // Check file's own status property first (from session update)
    if (file.status === "PROCESSING") {
      if (processingStartTime && processingEtaSec) {
        return {
          progress: Math.max(0, Math.min(100, clientProcessingProgress)),
          label: displayedRemainingSec != null ? `${formatTime(displayedRemainingSec)} remaining` : "Converting",
          showProgress: true,
        }
      }
      if (file.processing_progress) {
        const { progress_percent, remaining_seconds } = file.processing_progress
        return {
          progress: Math.max(0, Math.min(100, progress_percent || 0)),
          label: remaining_seconds != null ? `${formatTime(remaining_seconds)} remaining` : "Converting",
          showProgress: true,
        }
      }
    }

    if (file.status === "UPLOADING") {
      // Use per-file upload progress
      const percentage = file.upload_progress?.percentage ?? 0
      const safePercentage = Math.max(0, Math.min(100, percentage))
      let uploadLabel = `Uploading - ${Math.round(safePercentage)}%`

      const { uploadProgressConfirmed, eta, speed } = getJobUploadInfo(file)

      // Add ETA with speed in parentheses
      if (speed > 0 && eta) {
        uploadLabel += ` • ${formatTime(eta)} remaining (@${formatUploadSpeed(speed)})`
      } else if (speed > 0) {
        uploadLabel += ` (@${formatUploadSpeed(speed)})`
      }

      return {
        progress: safePercentage,
        label: uploadLabel,
        showProgress: true,
      }
    }

    if (file.status === "QUEUED") {
      // No progress shown - just waiting for worker to pick up the job
      return {
        progress: 0,
        label: "Queued",
        showProgress: false,
      }
    }

    // Fallback to global status for first item when converting
    if (!isConverting || index !== 0 || currentStatus === "COMPLETE") {
      // No progress for files that haven't started
      return null
    }

    switch (currentStatus) {
      case "UPLOADING":
        // The uploadProgress variable was undeclared. Use file.upload_progress?.percentage instead.
        const safeUploadProgress = Math.max(0, Math.min(100, file.upload_progress?.percentage ?? 0)) // Fallback to global if per-file isn't ready

        let uploadLabel = `Uploading - ${Math.round(safeUploadProgress)}%`

        // Add ETA with speed in parentheses
        if (uploadSpeed > 0 && uploadEta) {
          uploadLabel += ` • ${formatTime(uploadEta)} remaining (@${formatUploadSpeed(uploadSpeed)})`
        } else if (uploadSpeed > 0) {
          uploadLabel += ` (@${formatUploadSpeed(uploadSpeed)})`
        }

        return {
          progress: safeUploadProgress,
          label: uploadLabel,
          showProgress: true,
        }

      case "QUEUED":
        return {
          progress: 0,
          label: "Queued",
          showProgress: false,
        }

      case "PROCESSING":
        // Use only backend data; if missing, show 0%
        return {
          progress: file.processing_progress?.progress_percent ?? 0,
          label:
            file.processing_progress?.remaining_seconds != null
              ? `${formatTime(file.processing_progress.remaining_seconds)} remaining`
              : "Converting",
          showProgress: true,
        }

      default:
        return null
    }
  }

  const downloadFile = async (file: PendingUpload) => {
    if (!file.downloadId) return

    try {
      setDownloadingFiles((prev) => ({ ...prev, [file.name]: true }))

      const response = await fetchWithLicense(`/api/download/${file.downloadId}`)
      if (!response.ok) {
        const errText = await response.text()
        throw new Error(errText || "Failed to get download URL")
      }
      const data = await response.json()
      if (!data.signedUrl) {
        throw new Error(data.error || "No download URL returned")
      }
      window.location.href = data.signedUrl
      toast.success(`Downloading ${file.convertedName || file.name}`)
    } catch (error) {
      logError("Download error", file.downloadId, { error: error.message, fileName: file.name })
      toast.error("Download failed", {
        description: error instanceof Error ? error.message : "Failed to download file",
      })
    } finally {
      setTimeout(() => {
        setDownloadingFiles((prev) => ({ ...prev, [file.name]: false }))
      }, 1000)
    }
  }

  return (
    <div className="space-y-3">
      {onAddMoreFiles && onOpenSidebar && onStartConversion && (
        <div className="flex flex-col sm:flex-row gap-3 w-full">
          <Button
            variant="outline"
            onClick={() => {
              if (hasActiveJobs()) {
                toast.info("Please wait", {
                  description: "Wait for current files to finish converting before adding more files.",
                })
                return
              }
              onAddMoreFiles()
            }}
            disabled={isConverting || hasActiveJobs()}
            className="w-full sm:w-auto sm:flex-1 border-dashed border-2 hover:border-primary hover:bg-primary/5"
          >
            <FileText className="mr-2 h-4 w-4" />
            Add more files
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={() => {
              if (hasActiveJobs()) {
                toast.info("Please wait", {
                  description: "Wait for current files to finish converting before changing settings.",
                })
                return
              }
              onOpenSidebar()
            }}
            disabled={hasActiveJobs()}
            className="w-full sm:w-auto sm:flex-1"
          >
            <Settings className="h-5 w-5 mr-2" />
            Configure Options
          </Button>
          <Button
            size="lg"
            onClick={() => {
              if (hasActiveJobs()) {
                toast.info("Please wait", {
                  description: "Wait for current files to finish converting before starting a new batch.",
                })
                return
              }
              onStartConversion()
            }}
            disabled={isConverting || hasActiveJobs() || (isReadyToConvert && !isReadyToConvert())}
            className="w-full sm:w-auto sm:flex-1"
          >
            {isConverting ? (
              <>
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                Converting...
              </>
            ) : (
              "Start Conversion"
            )}
          </Button>
        </div>
      )}

      {items.map((file, index) => {
        const progressInfo = getProgressInfo(file, index)
        const isActive = isConverting && index === 0
        const jobRunning = isJobRunning(file)
        const { stage, progress, label, eta, isError } = getTimelineStage(file, index)

        return (
          <motion.div
            key={file.jobId ?? `${file.name}-${file.size}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <Card
              className={`
                transition-all group hover:scale-[1.005]
                ${
                  file.error
                    ? "border-danger/50 bg-danger/5"
                    : file.isConverted
                      ? "border-success/50 bg-success/5"
                      : "hover:border-muted-foreground/30"
                }
              `}
            >
              <div className="p-4 space-y-4">
                {/* Header: Filename and metadata */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div
                      className={`
                      w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0
                      ${
                        file.isConverted
                          ? "bg-success/10 text-success dark:text-success"
                          : file.error
                            ? "bg-danger/10 text-danger"
                            : "bg-muted"
                      }
                    `}
                    >
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate text-sm leading-tight">
                        {file.isConverted && file.convertedName ? file.convertedName : file.name}
                      </p>
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground mt-0.5">
                        {file.isConverted ? (
                          <>
                            {file.inputFileSize && file.outputFileSize && (
                              <span className="whitespace-nowrap">
                                {formatFileSize(file.inputFileSize)} → {formatFileSize(file.outputFileSize)}
                              </span>
                            )}
                            {file.actualDuration && (
                              <>
                                <span className="hidden xs:inline">•</span>
                                <span className="whitespace-nowrap">{formatTime(file.actualDuration)}</span>
                              </>
                            )}
                            {file.deviceProfile && deviceProfiles[file.deviceProfile] && (
                              <>
                                <span className="hidden xs:inline">•</span>
                                <span className="whitespace-nowrap hidden sm:inline">
                                  {deviceProfiles[file.deviceProfile]}
                                </span>
                              </>
                            )}
                          </>
                        ) : (
                          <>
                            <span className="whitespace-nowrap">{formatFileSize(file.size)}</span>
                            {file.deviceProfile && deviceProfiles[file.deviceProfile] && (
                              <>
                                <span>•</span>
                                <span className="whitespace-nowrap hidden sm:inline">
                                  {deviceProfiles[file.deviceProfile]}
                                </span>
                              </>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Status badge - shown on header for completed/error states */}
                  {(file.isConverted || file.error) && (
                    <div className="flex-shrink-0">{getStatusBadge(file, index)}</div>
                  )}
                </div>

                {/* Error message */}
                {file.error && (
                  <div className="flex items-start gap-2 text-sm text-destructive bg-destructive/5 rounded-lg p-3">
                    <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                    <span>{file.error}</span>
                  </div>
                )}

                {/* Timeline with inline action buttons */}
                {!file.isConverted &&
                  renderTimeline(
                    file,
                    index,
                    <>
                      {(() => {
                        const isDismissing = file.jobId
                          ? dismissingJobs.has(file.jobId) || cancellingJobs.has(file.jobId)
                          : false

                        // Disable ALL cancel buttons when ANY cancellation is in progress
                        const isAnyCancellationInProgress = cancellingJobs.size > 0
                        const isButtonDisabled = isDismissing || isAnyCancellationInProgress

                        if (file.error || jobRunning) {
                          return (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                if (jobRunning && onCancelJob) {
                                  log("[v0] Dismiss button clicked (cancelling job):", file.jobId)
                                  onCancelJob(file)
                                } else {
                                  onDismissJob?.(file)
                                }
                              }}
                              disabled={isButtonDisabled}
                              className={`
                                h-9 px-3
                                text-muted-foreground
                                hover:text-destructive hover:bg-destructive/10
                                active:bg-destructive/20
                                transition-colors duration-150
                                ${isButtonDisabled ? "opacity-60 pointer-events-none" : ""}
                              `}
                              aria-label={isDismissing ? "Dismissing..." : isAnyCancellationInProgress ? "Please wait..." : "Dismiss"}
                              title={isDismissing ? "Dismissing..." : isAnyCancellationInProgress ? "Another cancellation in progress" : "Dismiss"}
                            >
                              {isDismissing ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <XCircle className="h-4 w-4" />
                              )}
                              <span className="hidden sm:inline ml-1.5 text-sm font-medium">
                                {isDismissing ? "Dismissing" : "Dismiss"}
                              </span>
                            </Button>
                          )
                        } else if (!isActive && !jobRunning) {
                          // Not started - use same Dismiss-style button as converting state, but locally remove from queue
                          return (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onRemoveFile?.(file)}
                              className="
                                h-9 px-3
                                text-muted-foreground
                                hover:text-destructive hover:bg-destructive/10
                                active:bg-destructive/20
                                transition-colors duration-150
                              "
                              aria-label="Dismiss"
                              title="Dismiss"
                            >
                              <XCircle className="h-4 w-4" />
                              <span className="hidden sm:inline ml-1.5 text-sm font-medium">Dismiss</span>
                            </Button>
                          )
                        }
                        return null
                      })()}
                    </>,
                  )}

                {file.isConverted &&
                  renderTimeline(
                    file,
                    index,
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => downloadFile(file)}
                        disabled={downloadingFiles[file.name]}
                        size="sm"
                        className="shadow-sm"
                      >
                        {downloadingFiles[file.name] ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin sm:mr-2" />
                            <span className="hidden sm:inline">Downloading</span>
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4 sm:mr-2" />
                            <span className="hidden sm:inline">Download</span>
                          </>
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDismissJob?.(file)}
                        disabled={file.jobId ? dismissingJobs.has(file.jobId) : false}
                        className={`
                          h-9 px-3
                          text-muted-foreground
                          hover:text-destructive hover:bg-destructive/10
                          active:bg-destructive/20
                          transition-colors duration-150
                          ${file.jobId && dismissingJobs.has(file.jobId) ? "opacity-60 pointer-events-none" : ""}
                        `}
                        aria-label={file.jobId && dismissingJobs.has(file.jobId) ? "Dismissing..." : "Dismiss"}
                        title={file.jobId && dismissingJobs.has(file.jobId) ? "Dismissing..." : "Dismiss"}
                      >
                        {file.jobId && dismissingJobs.has(file.jobId) ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <XCircle className="h-4 w-4" />
                        )}
                        <span className="hidden sm:inline ml-1.5 text-sm font-medium">
                          {file.jobId && dismissingJobs.has(file.jobId) ? "Dismissing" : "Dismiss"}
                        </span>
                      </Button>
                    </div>,
                  )}
              </div>
            </Card>
          </motion.div>
        )
      })}
    </div>
  )
}
