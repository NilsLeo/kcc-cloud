"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { toast } from "sonner"
import { uploadFileAndConvert } from "@/lib/uploadFileAndConvert" // make sure you import it
import { ConversionQueue } from "./conversion-queue"
import { Footer } from "./footer"
import { DEVICE_PROFILES } from "@/lib/device-profiles"
import { fetchWithLicense, ensureSessionKey } from "@/lib/utils"
import { log, logError, logWarn, logDebug } from "@/lib/logger"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import type { ConvertedFileInfo } from "./converted-files" // Removed ConvertedFiles import since we're not using the separate section anymore
import { LoaderIcon, Settings, Clock, ChevronsRight } from "lucide-react"
import { AdvancedOptions } from "./advanced-options"
import { FileUploader } from "./file-uploader"
import { ALL_SUPPORTED_EXTENSIONS } from "@/lib/fileValidation"
import { DeviceSelector } from "./device-selector"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useJobWebSocket, type JobStatus } from "@/hooks/useJobWebSocket"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useConverterMode } from "@/contexts/converter-mode-context"

export type PendingUpload = {
  name: string
  size: number
  file: File
  error?: string
  jobId?: string
  status?: string
  isMonitoring?: boolean
  deviceProfile?: string // Override global device profile
  advancedOptions?: Partial<AdvancedOptionsType> // Override global advanced options
  isConverted?: boolean // Flag to indicate this is a converted file
  convertedName?: string // Output filename after conversion
  downloadId?: string // ID for downloading the converted file
  convertedTimestamp?: number // When the conversion completed
  outputFileSize?: number // Size of the converted file
  inputFileSize?: number // Original file size
  actualDuration?: number // Time taken for conversion
}

export type AdvancedOptionsType = {
  mangaStyle: boolean
  hq: boolean
  twoPanel: boolean
  webtoon: boolean
  targetSize: number
  noProcessing: boolean
  upscale: boolean
  stretch: boolean
  splitter: number
  gamma: number
  outputFormat: string
  author: string
  noKepub: boolean
  customWidth: number
  customHeight: number
}

// Helper function to convert frontend options to backend format
function convertAdvancedOptionsToBackend(options: AdvancedOptionsType) {
  return {
    manga_style: options.mangaStyle,
    hq: options.hq,
    two_panel: options.twoPanel,
    webtoon: options.webtoon,
    target_size: options.targetSize || undefined,
    no_processing: options.noProcessing,
    upscale: options.upscale,
    stretch: options.stretch,
    splitter: options.splitter,
    gamma: options.gamma || undefined,
    output_format: options.outputFormat !== "Auto" ? options.outputFormat : undefined,
    author: options.author || undefined,
    no_kepub: options.noKepub,
    custom_width: options.customWidth || undefined,
    custom_height: options.customHeight || undefined,
  }
}

export function MangaConverter({ contentType }: { contentType: "comic" | "manga" }) {
  const { mode } = useConverterMode()
  const isManga = mode === "manga"
  const isComic = mode === "comic"

  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([])
  const [selectedProfile, setSelectedProfile] = useState<string>("Placeholder")
  const [isConverting, setIsConverting] = useState(false)
  const [convertedFiles, setConvertedFiles] = useState<ConvertedFileInfo[]>([])
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [conversionProgress, setConversionProgress] = useState<number>(0)
  const [isUploaded, setIsUploaded] = useState<boolean>(false)
  const [eta, setEta] = useState<number | undefined>(undefined)
  const [remainingTime, setRemainingTime] = useState<number | undefined>(undefined)
  const [currentStatus, setCurrentStatus] = useState<string | undefined>(undefined)

  const [sidebarOpen, setSidebarOpen] = useState(false)

  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())

  const [needsConfiguration, setNeedsConfiguration] = useState(false)
  const [globalConfigPulsate, setGlobalConfigPulsate] = useState(false)

  const handleNeedsConfiguration = () => {
    setNeedsConfiguration(true)
    // Auto-reset after animation completes
    setTimeout(() => setNeedsConfiguration(false), 3000)
  }

  const handleGlobalConfigPulsate = () => {
    setGlobalConfigPulsate(true)
    setTimeout(() => setGlobalConfigPulsate(false), 3000)
  }

  const handleConfigureFile = (file: PendingUpload) => {
    // Open the sidebar
    setSidebarOpen(true)
  }

  const [advancedOptions, setAdvancedOptions] = useState<AdvancedOptionsType>({
    mangaStyle: isManga,
    hq: true,
    twoPanel: false,
    webtoon: false,
    targetSize: 400,
    noProcessing: false,
    upscale: true,
    stretch: false,
    splitter: 0,
    gamma: 0.0,
    outputFormat: "Auto",
    author: "KCC",
    noKepub: false,
    customWidth: 0,
    customHeight: 0,
  })

  const MAX_FILES = 10

  // Initialize WebSocket connection for real-time job updates
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"
  const { connected: wsConnected, subscribeToJob, unsubscribeFromJob, sendUploadProgress } = useJobWebSocket(apiUrl)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleAddMoreFiles = () => {
    fileInputRef.current?.click()
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(Array.from(e.target.files))
      // Reset input so same file can be selected again
      e.target.value = ""
    }
  }

  useEffect(() => {
    const loadPersistedJobs = async () => {
      try {
        const stored = localStorage.getItem("monitored_jobs")
        if (stored) {
          const jobs = JSON.parse(stored) as Array<{
            jobId: string
            name: string
            size: number
            status: string
            timestamp: number
            createdAt?: number
            inputFilename?: string
            inputFileSize?: number
            outputFilename?: string
            outputFileSize?: number
            downloadId?: string
            actualDuration?: number // Added for actual duration
            // Load per-file settings from storage
            deviceProfile?: string
            advancedOptions?: Partial<AdvancedOptionsType>
            // Add fields for converted files
            isConverted?: boolean
            convertedName?: string
            convertedTimestamp?: number
            outputFileSize?: number
            inputFileSize?: number
            actualDuration?: number
          }>

          // Filter out jobs older than 24 hours
          const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000
          const recentJobs = jobs.filter((job) => (job.createdAt || job.timestamp) > oneDayAgo)

          // Separate completed and active jobs
          const completedJobs = recentJobs.filter((job) => job.status === "COMPLETE")
          const activeJobs = recentJobs.filter(
            (job) => job.status !== "COMPLETE" && job.status !== "ERRORED" && job.status !== "CANCELLED",
          )

          // Restore completed jobs to converted files
          if (completedJobs.length > 0) {
            const convertedFilesFromStorage = completedJobs.map((job) => ({
              id: job.jobId,
              originalName: job.inputFilename || job.name,
              convertedName: job.outputFilename || job.name,
              downloadId: job.downloadId || job.jobId,
              timestamp: job.createdAt || job.timestamp,
              device: job.deviceProfile || "Unknown device",
              size: job.outputFileSize,
              inputFileSize: job.inputFileSize,
              actualDuration: job.actualDuration,
            }))

            setConvertedFiles(convertedFilesFromStorage)
          }

          // Create placeholder PendingUpload entries for active jobs
          if (activeJobs.length > 0) {
            const monitoringUploads: PendingUpload[] = activeJobs.map((job) => ({
              name: job.name,
              size: job.size,
              file: new File([], job.name), // Placeholder file
              jobId: job.jobId,
              status: job.status,
              isMonitoring: true,
              // Restore per-file settings
              deviceProfile: job.deviceProfile,
              advancedOptions: job.advancedOptions,
              // Restore converted file properties if applicable
              isConverted: job.status === "COMPLETE", // Mark as converted if status is COMPLETE
              convertedName: job.outputFilename,
              downloadId: job.downloadId || job.jobId,
              convertedTimestamp: job.createdAt || job.timestamp,
              outputFileSize: job.outputFileSize,
              inputFileSize: job.inputFileSize,
              actualDuration: job.actualDuration,
            }))

            setPendingUploads(monitoringUploads)

            // Start monitoring active jobs - check status first to see if they completed while offline
            for (const upload of monitoringUploads) {
              if (upload.jobId) {
                try {
                  // Check current status first
                  const statusResponse = await fetchWithLicense(`/api/job-status/${upload.jobId}`)
                  const statusData = await statusResponse.json()

                  if (statusData.status === "COMPLETE") {
                    // Job completed while offline - move to converted files
                    saveJobToStorage(upload.jobId, upload.name, upload.size, statusData.status, {
                      inputFilename: statusData.input_filename,
                      inputFileSize: statusData.input_file_size,
                      outputFilename: statusData.filename,
                      outputFileSize: statusData.output_file_size,
                      downloadId: upload.jobId,
                      actualDuration: statusData.actual_duration,
                      deviceProfile: statusData.device_profile,
                      isConverted: true, // Mark as converted
                      convertedName: statusData.filename,
                      convertedTimestamp: Date.now(),
                      outputFileSize: statusData.output_file_size,
                      inputFileSize: statusData.input_file_size,
                    })

                    setConvertedFiles((prev) => [
                      {
                        id: upload.jobId,
                        originalName: statusData.input_filename || upload.name,
                        convertedName: statusData.filename || upload.name,
                        downloadId: upload.jobId,
                        timestamp: Date.now(),
                        device: statusData.deviceProfile || "Unknown device",
                        size: statusData.output_file_size,
                        inputFileSize: statusData.input_file_size,
                        actualDuration: statusData.actual_duration,
                      },
                      ...prev,
                    ])

                    setPendingUploads((prev) => prev.filter((f) => f.jobId !== upload.jobId))
                  } else if (statusData.status === "CANCELLED") {
                    // Job was cancelled - silently remove without error
                    removeJobFromStorage(upload.jobId)
                    setPendingUploads((prev) => prev.filter((f) => f.jobId !== upload.jobId))
                  } else if (statusData.status === "ERRORED") {
                    // Job failed while offline - update status
                    saveJobToStorage(upload.jobId, upload.name, upload.size, statusData.status)
                    setPendingUploads((prev) =>
                      prev.map((f) =>
                        f.jobId === upload.jobId
                          ? { ...f, status: statusData.status, error: "Try a different file" }
                          : f,
                      ),
                    )
                  } else {
                    // Job still active - start monitoring
                    startJobMonitoring(upload.jobId, upload.name)
                  }
                } catch (error) {
                  logError(`Failed to check status for job ${upload.jobId}:`, error)
                  // If status check fails, still start monitoring
                  startJobMonitoring(upload.jobId, upload.name)
                }
              }
            }
          }

          // Update localStorage with filtered jobs
          if (recentJobs.length !== jobs.length) {
            localStorage.setItem("monitored_jobs", JSON.stringify(recentJobs))
          }
        }
      } catch (error) {
        logError("Failed to load persisted jobs:", error)
      }
    }

    // Initialize session key on page load to avoid delays during first conversion
    const initializeLicense = async () => {
      try {
        await ensureSessionKey()
        log("Session key initialized on page load")
      } catch (error) {
        logWarn("Failed to initialize session key on page load:", error)
        // Don't show error toast on page load - we'll handle it during conversion
      }
    }

    loadPersistedJobs()
    initializeLicense()
  }, []) // Run only once on mount

  const saveJobToStorage = (jobId: string, name: string, size: number, status: string, additionalData?: any) => {
    try {
      // Don't persist uploading jobs since they're ephemeral and can't be resumed
      if (status === "UPLOADING") {
        return
      }

      const stored = localStorage.getItem("monitored_jobs")
      const jobs = stored ? JSON.parse(stored) : []

      // Check if job already exists
      const existingIndex = jobs.findIndex((j: any) => j.jobId === jobId)
      const jobData = {
        jobId,
        name,
        size,
        status,
        timestamp: Date.now(),
        createdAt: Date.now(), // Keep original creation time
        ...additionalData,
      }

      if (existingIndex >= 0) {
        // Preserve original creation time when updating
        jobData.createdAt = jobs[existingIndex].createdAt || Date.now()
        jobs[existingIndex] = jobData
      } else {
        jobs.push(jobData)
      }

      localStorage.setItem("monitored_jobs", JSON.stringify(jobs))
    } catch (error) {
      logError("Failed to save job to storage:", error)
    }
  }

  const removeJobFromStorage = (jobId: string, force = false) => {
    try {
      const stored = localStorage.getItem("monitored_jobs")
      if (stored) {
        const jobs = JSON.parse(stored)

        if (force) {
          // Force removal (when user dismisses)
          const filtered = jobs.filter((j: any) => j.jobId !== jobId)
          localStorage.setItem("monitored_jobs", JSON.stringify(filtered))
        } else {
          // Don't remove completed jobs automatically - keep them for display
          // Only remove jobs that are truly orphaned or user-dismissed
          // CANCELLED jobs should be removed silently
          const filtered = jobs.filter(
            (j: any) =>
              j.jobId !== jobId || j.status === "COMPLETE" || j.status === "ERRORED",
          )
          localStorage.setItem("monitored_jobs", JSON.stringify(filtered))
        }
      }
    } catch (error) {
      logError("Failed to remove job from storage:", error)
    }
  }

  const handleDismissJob = (file: PendingUpload) => {
    if (file.jobId) {
      removeJobFromStorage(file.jobId, true) // Force removal when user dismisses
    }
    setPendingUploads((prev) => prev.filter((f) => f !== file))
  }

  // WebSocket-based job monitoring - replaces HTTP polling
  const startJobMonitoring = (jobId: string, filename: string) => {
    log(`[WebSocket] Starting monitoring for job ${jobId}`)

    // Subscribe to job status updates via WebSocket
    subscribeToJob(jobId, (statusData: JobStatus) => {
      log(`[WebSocket] Status update for ${jobId}:`, statusData)

      saveJobToStorage(jobId, filename, 0, statusData.status)

      // Update UI
      setPendingUploads((prev) => prev.map((f) => (f.jobId === jobId ? { ...f, status: statusData.status } : f)))

      if (statusData.status === "COMPLETE") {
        log("[v0] ========== CONVERSION COMPLETE ==========")
        log("[v0] Job ID:", jobId)
        log("[v0] Filename:", filename)
        log("[v0] Status Data:", statusData)
        log("[v0] Current pendingUploads before update:", pendingUploads)

        log("[v0] Conversion complete via WebSocket, updating file in place with metadata")

        // Save completed job to storage with additional data
        saveJobToStorage(jobId, filename, 0, statusData.status, {
          inputFilename: statusData.input_filename,
          inputFileSize: statusData.input_file_size,
          outputFilename: statusData.output_filename,
          outputFileSize: statusData.output_file_size,
          downloadId: jobId,
          actualDuration: statusData.actual_duration,
          deviceProfile: selectedProfile,
          isConverted: true,
          convertedName: statusData.output_filename,
          convertedTimestamp: Date.now(),
        })

        setPendingUploads((prev) => {
          log("[v0] Updating pendingUploads, looking for jobId:", jobId)
          const matchingFile = prev.find((f) => f.jobId === jobId)
          log("[v0] Found matching file:", matchingFile)

          const updated = prev.map((f) => {
            if (f.jobId === jobId) {
              const updatedFile = {
                ...f,
                isConverted: true,
                convertedName: statusData.output_filename || filename,
                downloadId: jobId,
                convertedTimestamp: Date.now(),
                outputFileSize: statusData.output_file_size,
                inputFileSize: statusData.input_file_size,
                actualDuration: statusData.actual_duration,
                status: "COMPLETE",
              }
              log("[v0] Updated file:", updatedFile)
              return updatedFile
            }
            return f
          })

          log("[v0] New pendingUploads after update:", updated)
          return updated
        })

        setConvertedFiles((prev) => [
          {
            id: Date.now().toString(),
            originalName: statusData.input_filename || filename,
            convertedName: statusData.output_filename || filename,
            downloadId: jobId,
            timestamp: Date.now(),
            device: DEVICE_PROFILES[selectedProfile] || selectedProfile,
            size: statusData.output_file_size,
            inputFileSize: statusData.input_file_size,
            actualDuration: statusData.actual_duration,
          },
          ...prev,
        ])

        // setPendingUploads((prev) => prev.filter((f) => f.jobId !== jobId))

        // Unsubscribe from updates
        unsubscribeFromJob(jobId)

        toast.success(`Conversion completed for ${filename}`)
        log("[v0] ========== END CONVERSION COMPLETE ==========")
      } else if (statusData.status === "CANCELLED") {
        // Silently remove cancelled jobs from UI
        setPendingUploads((prev) => prev.filter((f) => f.jobId !== jobId))
        unsubscribeFromJob(jobId)
        removeJobFromStorage(jobId)
      } else if (
        statusData.status === "failed" ||
        statusData.status === "ERRORED"
      ) {
        setPendingUploads((prev) =>
          prev.map((f) =>
            f.jobId === jobId
              ? { ...f, error: statusData.error || "Try a different file", status: statusData.status }
              : f,
          ),
        )

        // Unsubscribe from updates
        unsubscribeFromJob(jobId)

        toast.error(`Conversion failed: ${filename}`, {
          description: statusData.error || "Try a different file",
        })
      }
    })
  }

  const handleFileUpload = (files: File[]) => {
    if (isConverting) {
      toast("Conversion in progress", {
        description: "Please wait for current files to complete processing.",
      })
      return
    }

    if (files.length > MAX_FILES) {
      toast.warning(`Maximum ${MAX_FILES} files allowed`, {
        description: `Only the first ${MAX_FILES} files will be processed.`,
      })
      files = files.slice(0, MAX_FILES)
    }

    const newUploads = files.map((file) => ({
      name: file.name,
      size: file.size,
      file,
      deviceProfile: selectedProfile !== "Placeholder" ? selectedProfile : undefined,
      advancedOptions: { ...advancedOptions },
    }))

    setPendingUploads((prev) => [...prev, ...newUploads])
  }

  const getMinimalOptions = () => {
    if (isManga) {
      return {
        manga_style: advancedOptions.mangaStyle,
      }
    }
    return {}
  }

  const getFileSettings = (file: PendingUpload) => {
    return {
      deviceProfile: file.deviceProfile || selectedProfile,
      advancedOptions: file.advancedOptions || advancedOptions,
    }
  }

  const updateSelectedFilesSettings = (
    deviceProfile?: string,
    advancedOptionsUpdate?: Partial<AdvancedOptionsType>,
  ) => {
    setPendingUploads((prev) =>
      prev.map((file) => {
        if (selectedFiles.has(file.name)) {
          return {
            ...file,
            deviceProfile: deviceProfile !== undefined ? deviceProfile : file.deviceProfile,
            advancedOptions: advancedOptionsUpdate
              ? { ...(file.advancedOptions || advancedOptions), ...advancedOptionsUpdate }
              : file.advancedOptions,
          }
        }
        return file
      }),
    )
  }

  const toggleFileSelection = (fileName: string) => {
    setSelectedFiles((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(fileName)) {
        newSet.delete(fileName)
      } else {
        newSet.add(fileName)
      }
      return newSet
    })
  }

  const selectAllFiles = () => {
    setSelectedFiles(new Set(pendingUploads.map((f) => f.name)))
  }

  const clearSelection = () => {
    setSelectedFiles(new Set())
  }

  const areSettingsValid = () => {
    // Check if device is selected
    if (selectedProfile === "Placeholder") {
      return false
    }

    // If device is OTHER, validate required fields
    if (selectedProfile === "OTHER") {
      if (
        !advancedOptions.customWidth ||
        !advancedOptions.customHeight ||
        !advancedOptions.outputFormat ||
        advancedOptions.outputFormat === "Auto" ||
        advancedOptions.customWidth <= 0 ||
        advancedOptions.customHeight <= 0
      ) {
        return false
      }
    }

    return true
  }

  const handleApplySettings = () => {
    if (!areSettingsValid()) {
      if (selectedProfile === "Placeholder") {
        toast.warning("No device selected", {
          description: "Please select your E-Reader device.",
        })
      } else if (selectedProfile === "OTHER") {
        toast.warning("Missing required settings", {
          description:
            "Custom width, height, and output format (not 'Auto') are required when using 'Other' device profile.",
        })
      }
      return
    }

    // Apply settings to selected files if any are selected
    if (selectedFiles.size > 0) {
      updateSelectedFilesSettings(selectedProfile, advancedOptions)
      toast.success(`Settings applied to ${selectedFiles.size} file${selectedFiles.size !== 1 ? "s" : ""}`)
    }

    // Close sidebar
    setSidebarOpen(false)
  }

  const handleConvert = async () => {
    log(`[${new Date().toISOString()}] Start Conversion button pressed`)
    if (pendingUploads.length === 0) {
      toast.warning("No files to convert", {
        description: "Please upload at least one file to start conversion.",
      })
      return
    }

    const filesToConvert = pendingUploads.filter((file) => !file.isConverted)

    if (filesToConvert.length === 0) {
      toast.info("All files already converted", {
        description: "These files have already been converted. Add new files to convert more.",
      })
      return
    }

    if (selectedProfile === "Placeholder") {
      setNeedsConfiguration(true)
      toast.warning("No device selected", {
        description: "Please select your E-Reader device before starting the conversion.",
      })
      return
    }

    // Validate advanced options for OTHER profile
    if (selectedProfile === "OTHER") {
      if (
        !advancedOptions.customWidth ||
        !advancedOptions.customHeight ||
        !advancedOptions.outputFormat ||
        advancedOptions.outputFormat === "Auto"
      ) {
        toast.warning("Missing required settings", {
          description:
            "Custom width, height, and output format (not 'Auto') are required when using 'Other' device profile. Please configure them in Advanced Options.",
        })
        return
      }

      if (advancedOptions.customWidth <= 0 || advancedOptions.customHeight <= 0) {
        toast.warning("Invalid dimensions", {
          description: "Custom width and height must be greater than 0.",
        })
        return
      }
    }

    // Session key is already initialized on page load, no need to call ensureSessionKey() here

    // Prevent duplicate conversion requests
    if (isConverting) {
      logWarn("Conversion already in progress, ignoring duplicate request", {
        action: "duplicate_conversion_prevented",
        pendingFiles: pendingUploads.length,
      })
      return
    }
    setIsConverting(true)

    // Reset all progress states at the start of conversion
    setUploadProgress(0)
    setConversionProgress(0)
    setIsUploaded(false)
    setEta(undefined)
    setRemainingTime(undefined)
    setCurrentStatus(undefined)

    const filesToProcess = filesToConvert
    let hasErrors = false

    for (let i = 0; i < filesToProcess.length; i++) {
      const currentFile = filesToProcess[i]

      // Use a local variable for jobId within this loop iteration
      let jobId: string = currentFile.jobId || "" // Initialize jobId for the current file

      // Skip if the file is already being monitored (e.g., reloaded page)
      if (currentFile.isMonitoring && currentFile.jobId) {
        log("Skipping already monitored job", currentFile.jobId, { filename: currentFile.name })
        continue
      }

      const toastId = toast.loading(`Converting ${currentFile.name}... (${i + 1}/${filesToProcess.length})`, {
        duration: Number.POSITIVE_INFINITY,
      })

      try {
        const sessionKey = await ensureSessionKey()

        // Reset progress states for this file
        setUploadProgress(0)
        setIsUploaded(false)
        setConversionProgress(0)
        setEta(undefined)
        setRemainingTime(undefined)
        setCurrentStatus(undefined) // Will be set by first status poll

        let conversionComplete = false
        let errorMessage = null
        let filename = currentFile.name
        let inputFilename: string | undefined = undefined
        let inputFileSize: number | undefined = undefined
        let outputFileSize: number | undefined = undefined
        let conversionStartTime = null
        let projectedEta = null
        // jobId is now initialized above for the current file
        let isFirstStatusPoll = true
        let localCurrentStatus: string | undefined = undefined // Track status locally in the loop
        let statusData: any = {} // Declare statusData here

        log("=== CONVERSION FLOW START ===", {
          filename: currentFile.name,
          fileSize: currentFile.size,
          device: selectedProfile,
        })

        const fileSettings = getFileSettings(currentFile)
        const fileDeviceProfile = fileSettings.deviceProfile
        const fileAdvancedOptions = fileSettings.advancedOptions

        // Validate advanced options for OTHER profile
        if (fileDeviceProfile === "OTHER") {
          if (
            !fileAdvancedOptions.customWidth ||
            !fileAdvancedOptions.customHeight ||
            !fileAdvancedOptions.outputFormat ||
            fileAdvancedOptions.outputFormat === "Auto"
          ) {
            toast.warning("Missing required settings", {
              description: `File "${currentFile.name}": Custom width, height, and output format (not 'Auto') are required when using 'Other' device profile.`,
            })
            hasErrors = true
            continue
          }

          if (fileAdvancedOptions.customWidth <= 0 || fileAdvancedOptions.customHeight <= 0) {
            toast.warning("Invalid dimensions", {
              description: `File "${currentFile.name}": Custom width and height must be greater than 0.`,
            })
            hasErrors = true
            continue
          }
        }

        // Start upload and conversion process with immediate status polling
        let uploadPromise
        try {
          uploadPromise = uploadFileAndConvert(
            currentFile.file,
            sessionKey,
            fileDeviceProfile, // Use per-file device profile
            convertAdvancedOptionsToBackend(fileAdvancedOptions), // Use per-file advanced options
            // Upload progress callback for real-time UI updates
            (progress) => {
              setUploadProgress(progress)

              // Mark as uploaded when progress reaches 100%
              if (progress >= 100) {
                setIsUploaded(true)
                log("Upload completed", jobId, { uploadComplete: true })
              }
            },
            // Job ID callback - called immediately when job is created
            (createdJobId) => {
              jobId = createdJobId // Assign to the loop's jobId
              setCurrentStatus("UPLOADING") // Set initial status

              saveJobToStorage(jobId, currentFile.name, currentFile.size, "UPLOADING")
              setPendingUploads((prev) =>
                prev.map((f) => (f === currentFile ? { ...f, jobId, status: "UPLOADING", isMonitoring: true } : f)),
              )

              log("Job created - starting WebSocket monitoring", jobId, {
                initialStatus: "UPLOADING",
              })
            },
            // WebSocket upload progress callback for real-time backend updates
            sendUploadProgress,
          )
        } catch (uploadInitError) {
          logError("Failed to initialize upload", {
            error: uploadInitError.message,
            filename: currentFile.name,
          })
          throw new Error(`Upload initialization failed: ${uploadInitError.message}`)
        }

        // Wait for job ID to be available
        let waitCount = 0
        log("Waiting for job ID from upload initiation", {
          filename: currentFile.name,
        })

        while (!jobId) {
          // Wait for job ID (no timeout - will wait as long as needed)
          await new Promise((resolve) => setTimeout(resolve, 100))
          waitCount++

          // Log every second while waiting
          if (waitCount % 10 === 0) {
            log(`Still waiting for job ID... (${waitCount / 10}s)`, {
              waitCount,
              filename: currentFile.name,
            })
          }
        }

        log("Job ID received successfully", jobId, {
          waitTime: `${waitCount * 100}ms`,
          filename: currentFile.name,
        })

        log(`[${new Date().toISOString()}] Starting WebSocket monitoring for job ${jobId}`)
        log("Starting WebSocket monitoring", jobId, {
          reason: "Real-time status updates via WebSocket",
        })

        // Start upload process in background
        const uploadCompletePromise = uploadPromise.catch((uploadError) => {
          // Don't log user cancellations as errors
          if (!(uploadError as any).isUserCancellation && !uploadError.message?.includes("cancelled by user")) {
            logError("Upload or start signal failed", jobId, {
              error: uploadError.message,
            })
          }
          throw uploadError
        })

        // WebSocket-based job monitoring - replaces HTTP polling
        log(`[WebSocket] Starting real-time monitoring for job ${jobId}`)
        log("Starting WebSocket monitoring", jobId, {
          reason: "Real-time status updates via WebSocket",
        })

        // Create a Promise that resolves when job completes
        const jobCompletionPromise = new Promise<void>((resolve, reject) => {
          subscribeToJob(jobId, (wsStatus: JobStatus) => {
            log(`[WebSocket] Status update: ${wsStatus.status}`)
            statusData = wsStatus

            saveJobToStorage(jobId, currentFile.name, currentFile.size, wsStatus.status)

            // Update current status for progress bar and log status changes
            if (localCurrentStatus !== wsStatus.status) {
              const previousStatus = localCurrentStatus || "none"

              // Log first status or status transitions
              if (isFirstStatusPoll) {
                log(`[${new Date().toISOString()}] Initial WebSocket status: ${wsStatus.status}`)
                log("First WebSocket status", jobId, {
                  initial_status: wsStatus.status,
                })
                isFirstStatusPoll = false
              } else {
                log(`[${new Date().toISOString()}] Status transition: ${previousStatus} -> ${wsStatus.status}`)
                log(`STATUS TRANSITION: ${previousStatus} -> ${wsStatus.status}`, jobId, {
                  old_status: previousStatus,
                  new_status: wsStatus.status,
                  progress_percent: conversionProgress,
                  upload_progress: uploadProgress,
                })
              }

              localCurrentStatus = wsStatus.status
              setCurrentStatus(wsStatus.status)

              setPendingUploads((prev) => prev.map((f) => (f.jobId === jobId ? { ...f, status: wsStatus.status } : f)))
            }

            // Track conversion start time and ETA
            if (wsStatus.status === "PROCESSING" && conversionStartTime === null) {
              conversionStartTime = Date.now()
              projectedEta = wsStatus.projected_eta // In seconds
              setEta(projectedEta)
            }

            // Calculate or use provided progress
            if (wsStatus.progress_percent !== undefined) {
              setConversionProgress(wsStatus.progress_percent)
            } else if (conversionStartTime && projectedEta && wsStatus.status === "PROCESSING") {
              const elapsedSeconds = (Date.now() - conversionStartTime) / 1000
              const progressPercent = Math.min(95, (elapsedSeconds / projectedEta) * 100)
              const remaining = Math.max(0, projectedEta - elapsedSeconds)
              setConversionProgress(progressPercent)
              setRemainingTime(remaining)
            }

            // Update ETA and remaining time from WebSocket data
            if (wsStatus.projected_eta && !eta) {
              setEta(wsStatus.projected_eta)
            }
            if (wsStatus.remaining_seconds !== undefined) {
              setRemainingTime(wsStatus.remaining_seconds)
            }

            if (wsStatus.status === "COMPLETE") {
              log("Conversion completed successfully", jobId, {
                finalStatus: wsStatus.status,
                inputFilename: wsStatus.input_filename,
                inputFileSize: wsStatus.input_file_size,
                outputFilename: wsStatus.output_filename,
                outputFileSize: wsStatus.output_file_size,
                actualDuration: wsStatus.actual_duration,
              })
              conversionComplete = true
              filename = wsStatus.output_filename || currentFile.name
              inputFilename = wsStatus.input_filename
              inputFileSize = wsStatus.input_file_size
              outputFileSize = wsStatus.output_file_size
              setConversionProgress(100)
              setRemainingTime(0)

              // Save completed job to storage
              saveJobToStorage(jobId, currentFile.name, currentFile.size, "COMPLETE", {
                inputFilename: wsStatus.input_filename,
                inputFileSize: wsStatus.input_file_size,
                outputFilename: wsStatus.output_filename,
                outputFileSize: wsStatus.output_file_size,
                downloadId: jobId,
                actualDuration: wsStatus.actual_duration,
              })

              // Unsubscribe and resolve
              unsubscribeFromJob(jobId)
              resolve()
            } else if (wsStatus.status === "CANCELLED") {
              // Silently handle cancelled jobs
              log("Job cancelled", jobId, {
                finalStatus: wsStatus.status,
              })
              conversionComplete = true
              setConversionProgress(0)
              setRemainingTime(undefined)

              // Remove from storage and UI
              removeJobFromStorage(jobId)
              setPendingUploads((prev) => prev.filter((f) => f.jobId !== jobId))

              // Unsubscribe and reject
              unsubscribeFromJob(jobId)
              reject(new Error("Job cancelled"))
            } else if (
              wsStatus.status === "failed" ||
              wsStatus.status === "ERRORED" ||
              wsStatus.error
            ) {
              logError("Conversion failed", jobId, {
                finalStatus: wsStatus.status,
                error: wsStatus.error,
              })
              conversionComplete = true
              errorMessage = wsStatus.error || "Try a different file"
              setConversionProgress(0)
              setRemainingTime(undefined)

              saveJobToStorage(jobId, currentFile.name, currentFile.size, "ERRORED")

              // Unsubscribe and reject
              unsubscribeFromJob(jobId)
              reject(new Error(errorMessage))
            }
          })
        })

        // Wait for job to complete
        await jobCompletionPromise

        if (errorMessage) {
          throw new Error(errorMessage)
        }

        setPendingUploads((prev) =>
          prev.map((f) =>
            f.jobId === jobId
              ? {
                  ...f,
                  isConverted: true,
                  convertedName: filename,
                  downloadId: jobId,
                  convertedTimestamp: Date.now(),
                  outputFileSize: outputFileSize,
                  inputFileSize: inputFileSize,
                  actualDuration: statusData.actual_duration,
                  status: "COMPLETE",
                }
              : f,
          ),
        )

        setConvertedFiles((prev) => [
          {
            id: Date.now().toString(),
            originalName: inputFilename || currentFile.name,
            convertedName: filename,
            downloadId: jobId,
            timestamp: Date.now(),
            device: DEVICE_PROFILES[fileDeviceProfile] || fileDeviceProfile, // Use per-file device
            size: outputFileSize,
            inputFileSize: inputFileSize,
            actualDuration: statusData.actual_duration, // Corrected: use statusData from scope
          },
          ...prev,
        ])

        toast.success(`Conversion completed for ${currentFile.name}`, {
          id: toastId,
          duration: 6000,
        })

        // setPendingUploads((prev) => prev.filter((f) => f.jobId !== jobId))

        // Reset progress states for next file
        setUploadProgress(0)
        setConversionProgress(0)
        setIsUploaded(false)
        setEta(undefined)
        setRemainingTime(undefined)
        setCurrentStatus(undefined)
      } catch (error) {
        const actualErrorMessage = error instanceof Error ? error.message : String(error)

        // Check if this was a user cancellation (don't show error toast or log as error)
        if (
          actualErrorMessage.includes("cancelled by user") ||
          actualErrorMessage.includes("Upload cancelled") ||
          actualErrorMessage.includes("Job cancelled")
        ) {
          log("[v0] Job cancelled by user, cleaning up...")
          log("Job cancelled by user", jobId, { filename: currentFile.name })

          // Already removed from UI by WebSocket handler, just dismiss toast
          toast.dismiss(toastId)
          return // Exit without setting error state
        }

        // Only log actual errors (not cancellations)
        logError("Conversion error:", error)
        hasErrors = true

        setPendingUploads((prev) =>
          prev.map((f) =>
            f.jobId === jobId // Use the loop's jobId
              ? {
                  ...f,
                  error: "Try a different file",
                }
              : f,
          ),
        )

        toast.error(`Conversion failed: ${currentFile.name}`, {
          id: toastId,
          description: "Try a different file",
          duration: 8000,
        })
      }

      if (i < filesToProcess.length - 1) {
        await new Promise((resolve) => setTimeout(resolve, 500))
      }
    }

    log("All files processed", { totalFiles: filesToProcess.length })

    // Reset all progress states when conversion is complete
    setUploadProgress(0)
    setConversionProgress(0)
    setIsUploaded(false)
    setEta(undefined)
    setRemainingTime(undefined)
    setCurrentStatus(undefined)
    setIsConverting(false)
  }

  const handleConvertSingle = async (file: PendingUpload) => {
    log(`[${new Date().toISOString()}] Single file conversion started for:`, file.name)

    if (file.isConverted) {
      toast.info("File already converted", {
        description: "This file has already been converted.",
      })
      return
    }

    if (selectedProfile === "Placeholder") {
      setNeedsConfiguration(true)
      toast.warning("No device selected", {
        description: "Please select your E-Reader device before starting the conversion.",
      })
      return
    }

    // Validate advanced options for OTHER profile
    if (selectedProfile === "OTHER") {
      const fileSettings = getFileSettings(file)
      const fileAdvancedOptions = fileSettings.advancedOptions

      if (
        !fileAdvancedOptions.customWidth ||
        !fileAdvancedOptions.customHeight ||
        !fileAdvancedOptions.outputFormat ||
        fileAdvancedOptions.outputFormat === "Auto"
      ) {
        toast.warning("Missing required settings", {
          description:
            "Custom width, height, and output format (not 'Auto') are required when using 'Other' device profile. Please configure them in Advanced Options.",
        })
        return
      }

      if (fileAdvancedOptions.customWidth <= 0 || fileAdvancedOptions.customHeight <= 0) {
        toast.warning("Invalid dimensions", {
          description: "Custom width and height must be greater than 0.",
        })
        return
      }
    }

    // Session key is already initialized on page load, no need to call ensureSessionKey() here

    // Create a temporary conversion queue with just this file
    const tempQueue = [file]

    // Reuse the existing conversion logic by temporarily setting pendingUploads
    const originalQueue = [...pendingUploads]
    setPendingUploads(tempQueue)

    // Call the main conversion handler
    await handleConvert()

    // Restore the original queue (the conversion will have updated the file status)
    // Note: We don't actually restore because handleConvert already updates the state correctly
  }

  const handleCancelJob = (file: PendingUpload) => {
    if (!file.jobId) {
      logError("[v0] Cannot cancel: No job ID")
      toast.error("Cannot cancel: No job ID")
      return
    }

    log("[v0] Cancel requested for job:", file.jobId, "file:", file.name)

    // Log in background (don't block UI)
    log("Cancel button clicked", file.jobId, {
      filename: file.name,
      file_size: file.file.size,
    })

    // IMMEDIATELY abort active upload if it's in progress
    import("@/lib/uploadFileAndConvert")
      .then(({ abortUpload }) => {
        const uploadAborted = abortUpload(file.jobId)
        if (uploadAborted) {
          log("[v0] Upload XHR aborted immediately for:", file.jobId)
        }
      })
      .catch((error) => {
        // Silently handle expected cancellation errors
        if (error?.message?.includes("Upload cancelled")) {
          log("[v0] Upload cancellation handled gracefully")
        } else {
          logError("[v0] Unexpected error during upload abort:", error)
        }
      })

    // Check if this was the active job BEFORE removing
    const wasActiveJob = pendingUploads.findIndex((f) => f.jobId === file.jobId) === 0 && isConverting

    // Dismiss any active conversion toasts for this job
    toast.dismiss()

    // IMMEDIATELY remove the job card from UI
    setPendingUploads((prev) => prev.filter((f) => f.jobId !== file.jobId))

    // Reset conversion state if this was the active job
    if (wasActiveJob) {
      setIsConverting(false)
      setUploadProgress(0)
      setConversionProgress(0)
      setEta(undefined)
      setRemainingTime(undefined)
      setCurrentStatus(undefined)
    }

    // Unsubscribe from WebSocket updates for this job
    unsubscribeFromJob(file.jobId)

    // Remove from localStorage
    removeJobFromStorage(file.jobId)

    // Backend cancellation continues in background (don't block UI on this)
    ;(async () => {
      try {
        const response = await fetchWithLicense(`/api/jobs/${file.jobId}/cancel`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || "Failed to cancel job")
        }

        const data = await response.json()

        log("Job cancellation confirmed by backend", file.jobId, {
          filename: file.name,
          new_status: data.status,
        })

        toast.success(`Cancelled ${file.name}`)
      } catch (error) {
        logError("[v0] Backend cancel failed (UI already removed):", error)
        logError("Job cancellation failed in backend", file.jobId, {
          error: error instanceof Error ? error.message : String(error),
          filename: file.name,
        })
        // Don't show error toast since job is already removed from UI
      }
    })()
  }

  const handleAdvancedOptionsChange = (newOptions: Partial<AdvancedOptionsType>) => {
    setAdvancedOptions((prev) => ({
      ...prev,
      ...newOptions,
      targetSize: newOptions.webtoon !== undefined ? (newOptions.webtoon ? 100 : 400) : prev.targetSize,
    }))
  }

  const handleReorder = (newOrder: PendingUpload[]) => {
    setPendingUploads(newOrder)
  }

  const clearConvertedFiles = () => {
    // Remove all completed jobs from localStorage
    try {
      const stored = localStorage.getItem("monitored_jobs")
      if (stored) {
        const jobs = JSON.parse(stored)
        const filteredJobs = jobs.filter((job: any) => job.status !== "COMPLETE")
        localStorage.setItem("monitored_jobs", JSON.stringify(filteredJobs))
      }
    } catch (error) {
      logError("Failed to clear completed jobs from localStorage:", error)
    }

    setConvertedFiles([])
  }

  const removeConvertedFile = (file: ConvertedFileInfo) => {
    // Remove specific job from localStorage
    try {
      const stored = localStorage.getItem("monitored_jobs")
      if (stored) {
        const jobs = JSON.parse(stored)
        const filteredJobs = jobs.filter((job: any) => job.jobId !== file.downloadId)
        localStorage.setItem("monitored_jobs", JSON.stringify(filteredJobs))
      }
    } catch (error) {
      logError("Failed to remove job from localStorage:", error)
    }

    // Remove from React state
    setConvertedFiles((prev) => prev.filter((f) => f.id !== file.id))
  }

  const isReadyToConvert = () => {
    const hasFilesToConvert = pendingUploads.some((file) => !file.isConverted)
    return hasFilesToConvert && selectedProfile !== "Placeholder" && !isConverting
  }

  const getValidFileCount = () => {
    return pendingUploads.filter((file) => !file.error && !file.isConverted).length
  }

  const handleConvertButtonClick = () => {
    // Prevent any action if already converting
    if (isConverting) {
      return
    }

    if (isReadyToConvert()) {
      handleConvert()
    } else {
      if (selectedProfile === "Placeholder") {
        handleGlobalConfigPulsate()
      }

      if (pendingUploads.length === 0) {
        toast.warning("No files to convert", {
          description: "Please upload at least one file to start conversion.",
        })
      } else if (selectedProfile === "Placeholder") {
        toast.warning("No device selected", {
          description: "Please select your E-Reader device before starting the conversion.",
        })
      } else if (getValidFileCount() === 0) {
        toast.info("All files converted", {
          description: "All uploaded files have already been converted.",
        })
      }
    }
  }

  const getProgress = () => {
    const hasFiles = pendingUploads.length > 0
    const hasDevice = selectedProfile !== "Placeholder"
    if (!hasFiles) return 0
    if (hasFiles && !hasDevice) return 33
    if (hasFiles && hasDevice) return 66
    return 100
  }

  const [isButtonSticky, setIsButtonSticky] = useState(false)
  const buttonContainerRef = useRef<HTMLDivElement>(null)

  // Debug function to reset converting state

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        // When the button container is not intersecting (out of view), make it sticky
        setIsButtonSticky(!entry.isIntersecting)
      },
      {
        threshold: 0,
        rootMargin: "0px 0px -80px 0px", // Account for bottom padding
      },
    )

    if (buttonContainerRef.current) {
      observer.observe(buttonContainerRef.current)
    }

    return () => {
      if (buttonContainerRef.current) {
        observer.unobserve(buttonContainerRef.current)
      }
    }
  }, [])

  const queueRef = useRef<PendingUpload[]>([])

  useEffect(() => {
    queueRef.current = [...pendingUploads]
  }, [pendingUploads])

  useEffect(() => {
    if (sidebarOpen || selectedProfile !== "Placeholder") {
      setNeedsConfiguration(false)
      setGlobalConfigPulsate(false)
    }
  }, [sidebarOpen, selectedProfile])

  return (
    <>
      <div className="flex flex-col gap-6 max-w-6xl mx-auto pb-24">
        <section className="text-center space-y-2">
          <h1 className={`text-4xl font-bold tracking-tight ${isComic ? "font-bungee" : "font-kosugi-maru"}`}>
            {isComic ? "COMIC CONVERTER" : "マンガコンバーター"}
          </h1>
          <p className="text-lg text-muted-foreground">
            Convert your {isComic ? "comic" : "manga"} files to e-reader formats
          </p>
        </section>

        {convertedFiles.length > 0 && (
          <div className="space-y-3">
            {/* <ConvertedFiles removed> */}
            {process.env.NEXT_PUBLIC_TTL && (
              <Alert variant="success">
                <Clock className="h-4 w-4" />
                <AlertDescription>
                  Files will be available for {Number.parseInt(process.env.NEXT_PUBLIC_TTL) * 24} hours after conversion
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Files</CardTitle>
                <CardDescription>
                  {pendingUploads.length > 0
                    ? `${pendingUploads.length} file${pendingUploads.length !== 1 ? "s" : ""} ${getValidFileCount() > 0 ? `(${getValidFileCount()} ready to convert)` : "(all converted)"}`
                    : "Upload your comic or manga files to get started"}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {pendingUploads.length === 0 ? (
              <FileUploader
                onFilesSelected={handleFileUpload}
                disabled={isConverting}
                acceptedTypes={ALL_SUPPORTED_EXTENSIONS}
                maxFiles={MAX_FILES}
                contentType={contentType}
              />
            ) : (
              <>
                <ConversionQueue
                  pendingUploads={pendingUploads}
                  isConverting={isConverting}
                  onConvert={handleConvert}
                  onConvertSingle={handleConvertSingle}
                  onCancelJob={handleCancelJob}
                  selectedProfile={selectedProfile}
                  globalAdvancedOptions={advancedOptions}
                  onReorder={handleReorder}
                  showAsUploadedFiles={false}
                  onRemoveFile={(file) => setPendingUploads((prev) => prev.filter((f) => f !== file))}
                  onDismissJob={handleDismissJob}
                  uploadProgress={uploadProgress}
                  conversionProgress={conversionProgress}
                  isUploaded={isUploaded}
                  eta={eta}
                  remainingTime={remainingTime}
                  currentStatus={currentStatus}
                  selectedFiles={selectedFiles}
                  onToggleFileSelection={toggleFileSelection}
                  onSelectAll={selectAllFiles}
                  onClearSelection={clearSelection}
                  onUpdateSelectedFiles={updateSelectedFilesSettings}
                  deviceProfiles={DEVICE_PROFILES}
                  onAddMoreFiles={handleAddMoreFiles}
                  onNeedsConfiguration={handleNeedsConfiguration}
                  onConfigureFile={handleConfigureFile}
                />
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileInputChange}
                  accept={ALL_SUPPORTED_EXTENSIONS.join(",")}
                  multiple
                  className="hidden"
                  disabled={isConverting}
                />
              </>
            )}
          </CardContent>
        </Card>

        <Footer />
      </div>

      {/* CHANGE: Buttons now only show when files are selected via checkbox */}
      {selectedFiles.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 bg-background/95 backdrop-blur-sm border-t shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
          <div className="max-w-6xl mx-auto p-4">
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="lg"
                onClick={() => setSidebarOpen(true)}
                className={`flex-1 h-12 ${
                  globalConfigPulsate || needsConfiguration
                    ? isComic
                      ? "bg-yellow-500/20 hover:bg-yellow-500/30 border-yellow-500 animate-pulse shadow-lg"
                      : "bg-red-600/20 hover:bg-red-600/30 border-red-600 animate-pulse shadow-lg"
                    : ""
                }`}
              >
                <Settings className="h-5 w-5 mr-2" />
                Configure
                {selectedFiles.size > 0 && (
                  <span className="ml-2 px-2 py-0.5 text-xs rounded-full bg-primary text-primary-foreground">
                    {selectedFiles.size}
                  </span>
                )}
              </Button>

              <Button
                onClick={handleConvertButtonClick}
                disabled={isConverting || !isReadyToConvert()}
                size="lg"
                className={`flex-1 h-12 text-base transition-all duration-300 ${
                  isReadyToConvert()
                    ? isComic
                      ? "bg-yellow-500 hover:bg-yellow-600 text-black shadow-lg hover:shadow-xl"
                      : "bg-red-600 hover:bg-red-700 text-white shadow-lg hover:shadow-xl"
                    : // Added red/yellow with 30% opacity for disabled state
                      isComic
                      ? "bg-yellow-500/30 text-yellow-900 dark:text-yellow-100 cursor-not-allowed"
                      : "bg-red-600/30 text-red-100 cursor-not-allowed"
                }`}
              >
                {isConverting ? (
                  <>
                    <LoaderIcon className="mr-2 h-5 w-5 animate-spin" />
                    Converting {getValidFileCount() > 1 ? `${getValidFileCount()} files` : "file"}...
                  </>
                ) : isReadyToConvert() ? (
                  <>Start Conversion{getValidFileCount() > 1 ? ` (${getValidFileCount()} files)` : ""}</>
                ) : (
                  <>
                    {pendingUploads.length === 0 && "Upload files to start"}
                    {pendingUploads.length > 0 && getValidFileCount() === 0 && "All files converted"}
                    {pendingUploads.length > 0 &&
                      getValidFileCount() > 0 &&
                      selectedProfile === "Placeholder" &&
                      "Select a device to continue"}
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent className="fixed z-50 gap-4 bg-background p-6 pb-0 shadow-lg transition ease-in-out data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:duration-300 data-[state=open]:duration-500 inset-y-0 right-0 h-full border-l data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right w-full sm:max-w-lg overflow-y-auto [&>button]:hidden">
          <Button
            variant="outline"
            size="icon"
            className="absolute -left-12 top-6 h-12 w-12 rounded-l-md rounded-r-none border-r-0 shadow-lg bg-background hover:bg-accent hover:shadow-xl transition-all duration-200 border-2"
            onClick={() => setSidebarOpen(false)}
            aria-label="Collapse configuration panel"
          >
            <ChevronsRight className="h-6 w-6" />
          </Button>

          <SheetHeader>
            <SheetTitle>
              {selectedFiles.size > 0
                ? `Configure ${selectedFiles.size} Selected File${selectedFiles.size !== 1 ? "s" : ""}`
                : "Configure Options"}
            </SheetTitle>
            <SheetDescription>
              {selectedFiles.size > 0
                ? "Changes will apply only to selected files"
                : "Set default options for all files"}
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-6 mt-6 pb-32">
            {/* Device Selector */}
            <div className="space-y-2">
              <Label className="text-base font-semibold">E-Reader Device</Label>
              <DeviceSelector
                selectedProfile={selectedProfile}
                onProfileChange={(profile) => {
                  setSelectedProfile(profile)
                  if (selectedFiles.size > 0) {
                    updateSelectedFilesSettings(profile, undefined)
                  }
                }}
                deviceProfiles={DEVICE_PROFILES}
              />
            </div>

            {/* Advanced Options */}
            <div className="space-y-2">
              <Label className="text-base font-semibold">Advanced Options</Label>
              <AdvancedOptions
                options={advancedOptions}
                onChange={(newOptions) => {
                  handleAdvancedOptionsChange(newOptions)
                  if (selectedFiles.size > 0) {
                    updateSelectedFilesSettings(undefined, newOptions)
                  }
                }}
                deviceProfile={selectedProfile}
                contentType={contentType}
              />
            </div>
          </div>

          <div className="sticky bottom-0 left-0 right-0 p-6 bg-background/95 backdrop-blur-sm border-t shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]">
            <Button
              onClick={handleApplySettings}
              disabled={!areSettingsValid()}
              size="lg"
              className={`w-full ${
                isComic ? "bg-yellow-500 hover:bg-yellow-600 text-black" : "bg-red-600 hover:bg-red-700 text-white"
              }`}
            >
              Apply Settings
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
