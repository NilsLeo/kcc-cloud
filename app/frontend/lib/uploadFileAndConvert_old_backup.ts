import { ensureSessionKey } from "@/lib/utils" // you already have this
import { log, logError, logWarn } from "./logger"
import { MultipartUploadClient } from "./MultipartUploadClient"

// Track active jobs to prevent duplicates
const activeJobs = new Set<string>()

// Track active uploads for cancellation (jobId -> {fileKey, client})
const activeUploads = new Map<string, { fileKey: string; client: MultipartUploadClient }>()

// Export function to abort an active upload
export function abortUpload(jobId: string): boolean {
  const uploadInfo = activeUploads.get(jobId)
  if (uploadInfo) {
    log(`[UPLOAD] Aborting multipart upload for job: ${jobId}`)

    // Abort multipart upload
    uploadInfo.client.abortUpload(jobId)

    activeUploads.delete(jobId)
    // Also remove from activeJobs to allow re-upload
    activeJobs.delete(uploadInfo.fileKey)
    log(`[UPLOAD] Removed ${uploadInfo.fileKey} from activeJobs, can now be re-uploaded`)
    return true
  }
  return false
}

// Multipart upload function (now used for ALL files)
async function uploadFileViaMultipart(
  file: File,
  jobId: string,
  sessionKey: string,
  fileKey: string,
  onProgress: (progress: number, fullProgressData?: any) => void,
  sendUploadProgress?: (jobId: string, bytesUploaded: number) => void,
): Promise<void> {
  // Dynamic part sizing: use measured client upload speed (if available) and
  // current global upload load to choose part size and per-file concurrency
  // that avoid timeouts and reduce retries.
  const MIN_PART_SIZE = 5 * 1024 * 1024 // 5 MB (S3 requirement)
  const MAX_PART_SIZE = 25 * 1024 * 1024 // 25 MB cap per part to keep parts manageable
  const DEFAULT_TARGET_PARTS = 100 // fallback

  // Load last measured upload speed (bytes/sec) from localStorage
  let measuredBps = 0
  try {
    const saved = localStorage.getItem("upload_speed_bps")
    if (saved) measuredBps = Math.max(0, Number.parseInt(saved))
  } catch {}

  // Fallback baseline if no measurement (rough default 2 MB/s)
  const BASELINE_BPS = 2 * 1024 * 1024
  const speedBps = measuredBps > 0 ? measuredBps : BASELINE_BPS

  // Account for concurrent uploads in progress (including this one)
  // Use a conservative split of available bandwidth across uploads
  const concurrentUploads = activeUploads.size + 1
  const effectiveBps = Math.max(64 * 1024, Math.floor(speedBps / concurrentUploads)) // floor to at least 64KB/s

  // Safety buffer to account for variability
  const SAFETY = 0.7
  // Target per-part upload duration in seconds
  const TARGET_PART_SECONDS = 25

  // Compute recommended part size from speed and safety buffer
  let recommendedPartSize = Math.floor(effectiveBps * SAFETY * TARGET_PART_SECONDS)
  if (recommendedPartSize < MIN_PART_SIZE) recommendedPartSize = MIN_PART_SIZE
  if (recommendedPartSize > MAX_PART_SIZE) recommendedPartSize = MAX_PART_SIZE

  // If file is very small, just single part
  let partSize: number
  let numParts: number
  if (file.size <= MIN_PART_SIZE) {
    partSize = file.size
    numParts = 1
  } else {
    partSize = recommendedPartSize
    numParts = Math.max(1, Math.ceil(file.size / partSize))
    // Keep parts in a reasonable range
    if (numParts > DEFAULT_TARGET_PARTS * 2) {
      numParts = DEFAULT_TARGET_PARTS * 2
      partSize = Math.ceil(file.size / numParts)
    }
  }

  log(`[MULTIPART UPLOAD] Starting multipart upload`, {
    job_id: jobId,
    file_name: file.name,
    file_size: file.size,
    part_size: partSize,
    num_parts: numParts,
    progress_granularity: `${(100 / numParts).toFixed(1)}%`,
  })

  // Set concurrency based on effective per-upload speed: slower → fewer parts
  let maxConcurrent = 6
  if (effectiveBps < 1 * 1024 * 1024)
    maxConcurrent = 3 // <1 MB/s
  else if (effectiveBps < 2 * 1024 * 1024) maxConcurrent = 4
  else if (effectiveBps < 5 * 1024 * 1024) maxConcurrent = 5
  else maxConcurrent = 6

  // Share a global concurrency budget across simultaneous uploads
  const globalMax = Number(process.env.NEXT_PUBLIC_GLOBAL_MAX_CONCURRENT_PARTS || "8")
  const perUploadShare = Math.max(1, Math.floor(globalMax / concurrentUploads))
  maxConcurrent = Math.max(1, Math.min(maxConcurrent, perUploadShare))

  // Derive upload timeout: roughly 3x expected per-part time to account for S3 latency, with bounds
  const expectedPartSeconds = partSize / Math.max(1, effectiveBps * SAFETY)
  const calculatedTimeout = Math.ceil(expectedPartSeconds * 3000)

  // Allow override via env var, otherwise use calculated timeout with bounds (180s - 300s)
  const envTimeout = process.env.NEXT_PUBLIC_UPLOAD_TIMEOUT_MS
    ? Number(process.env.NEXT_PUBLIC_UPLOAD_TIMEOUT_MS)
    : null

  const uploadTimeoutMs = envTimeout || Math.min(300_000, Math.max(180_000, calculatedTimeout))

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"
  const client = new MultipartUploadClient(apiUrl, sessionKey, {
    partSize: partSize,
    maxConcurrentParts: maxConcurrent,
    uploadTimeoutMs,
  })

  log("[MULTIPART UPLOAD] Load-aware settings", {
    job_id: jobId,
    concurrent_uploads: concurrentUploads,
    effective_bps: effectiveBps,
    per_upload_concurrency: maxConcurrent,
    global_max_concurrency: Number(process.env.NEXT_PUBLIC_GLOBAL_MAX_CONCURRENT_PARTS || "8"),
    upload_timeout_ms: uploadTimeoutMs,
    upload_timeout_seconds: Math.round(uploadTimeoutMs / 1000),
    timeout_source: envTimeout ? "env_var" : "calculated",
  })

  // Register for cancellation
  activeUploads.set(jobId, { fileKey, client })

  // Track last logged percentage threshold (0, 10, 20, etc.)
  let lastLoggedThreshold = -1

  try {
    await client.uploadFile(file, jobId, (progress) => {
      // Update local progress with full progress data for ETA calculation
      onProgress(progress.percentage, progress)

      // Send progress via WebSocket
      if (sendUploadProgress) {
        sendUploadProgress(jobId, progress.uploadedBytes)
      }

      // Only log every 10% increment
      const currentThreshold = Math.floor(progress.percentage / 10)
      if (currentThreshold !== lastLoggedThreshold) {
        lastLoggedThreshold = currentThreshold
        log(`[MULTIPART UPLOAD] Progress update`, {
          job_id: jobId,
          completed_parts: progress.completedParts,
          total_parts: progress.totalParts,
          percentage: progress.percentage.toFixed(1),
        })
      }
    })

    log(`[MULTIPART UPLOAD] Upload completed successfully`, {
      job_id: jobId,
      file_name: file.name,
    })
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    // Only log as error if it's not an expected abort/cancellation
    if (errorMessage.includes("Upload aborted") || errorMessage.includes("cancelled by user")) {
      log(`[MULTIPART UPLOAD] Upload cancelled`, {
        job_id: jobId,
      })
    } else {
      logError(`[MULTIPART UPLOAD] Upload failed`, {
        job_id: jobId,
        error: errorMessage,
      })
    }
    throw error
  } finally {
    // Cleanup
    activeUploads.delete(jobId)
  }
}

export async function uploadFileAndConvert(
  file: File,
  sessionKey: string,
  deviceProfile?: string,
  advancedOptions?: Record<string, any>,
  onUploadProgress?: (progress: number, fullProgressData?: any) => void,
  onJobCreated?: (jobId: string) => void,
  sendUploadProgress?: (jobId: string, bytesUploaded: number) => void,
) {
  const startTime = performance.now()
  log(`[TIMING] uploadFileAndConvert started for file: ${file.name} (${file.size} bytes)`)

  // Create a unique identifier for this file to prevent duplicate processing
  const fileKey = `${file.name}-${file.size}-${file.lastModified}`

  // Track if upload was cancelled
  const uploadCancelled = false

  // Check if this file is already being processed
  if (activeJobs.has(fileKey)) {
    logWarn("Duplicate job request detected and blocked", {
      filename: file.name,
      file_size: file.size,
      file_key: fileKey,
      action: "duplicate_job_prevented",
    })
    throw new Error(
      `File "${file.name}" is already being processed. Please wait for the current conversion to complete.`,
    )
  }

  // Mark this file as being processed
  activeJobs.add(fileKey)

  try {
    log("=== UPLOAD FLOW START ===", {
      filename: file.name,
      file_size: file.size,
      device_profile: deviceProfile,
      advanced_options: advancedOptions,
      file_key: fileKey,
      flow_step: "upload_start",
    })

    // Show 1% progress immediately to indicate upload has started
    if (onUploadProgress) {
      onUploadProgress(1, undefined)
    }

    async function createJob(currentLicenseKey: string) {
      const jobCreateStart = performance.now()
      log(`[${new Date().toISOString()}] Sending POST request to /api/jobs`)
      const jobRes = await fetch("/api/jobs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Key": currentLicenseKey,
        },
        body: JSON.stringify({
          filename: file.name,
          file_size: file.size,
          device_profile: deviceProfile,
          advanced_options: advancedOptions,
        }),
      })

      if (!jobRes.ok) {
        let errorMessage = `Failed to create job (HTTP ${jobRes.status})`
        try {
          const errorData = await jobRes.json()
          if (errorData.error) {
            errorMessage = errorData.error

            if (
              (jobRes.status === 401 || jobRes.status === 403) &&
              (errorData.error.includes("Invalid session key") || errorData.error.includes("Unauthorized"))
            ) {
              logWarn("Invalid/unauthorized session key, clearing localStorage and obtaining fresh session", {
                status: jobRes.status,
                error: errorData.error,
              })
              localStorage.removeItem("mangaconverter_session_key")

              // Obtain fresh session from backend
              const newLicenseKey = await ensureSessionKey(true)
              log("Fresh session obtained from backend, retrying job creation", {
                hasNewLicense: !!newLicenseKey,
              })

              // Retry the request with new session
              const retryRes = await fetch("/api/jobs", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  "X-Session-Key": newLicenseKey,
                },
                body: JSON.stringify({
                  filename: file.name,
                  file_size: file.size,
                  device_profile: deviceProfile,
                  advanced_options: advancedOptions,
                }),
              })

              if (!retryRes.ok) {
                const retryError = await retryRes
                  .json()
                  .catch(() => ({ error: "Failed to create job after session refresh" }))
                throw new Error(
                  retryError.error || `Failed to create job after session refresh (HTTP ${retryRes.status})`,
                )
              }

              const retryData = await retryRes.json()
              log(
                `[${new Date().toISOString()}] POST /jobs response received after session refresh for job: ${retryData.job_id}`,
              )
              log(`[TIMING] Job creation with retry took ${(performance.now() - jobCreateStart).toFixed(2)}ms`)

              // Update the outer sessionKey variable
              sessionKey = newLicenseKey

              return retryData
            }
          }
        } catch (error) {
          // If this is our retry error, throw it
          if (error instanceof Error && error.message.includes("session refresh")) {
            throw error
          }
          // Otherwise, use the default message
        }
        throw new Error(errorMessage)
      }

      const jobData = await jobRes.json()
      log(`[${new Date().toISOString()}] POST /jobs response received for job: ${jobData.job_id}`)
      log(`[TIMING] Job creation took ${(performance.now() - jobCreateStart).toFixed(2)}ms`)
      return jobData
    }

    const jobData = await createJob(sessionKey)

    // Notify that job was created - session updates will track status immediately
    log("Job creation successful, notifying callback", jobData.job_id, {
      hasCallback: !!onJobCreated,
      jobId: jobData.job_id,
    })

    if (onJobCreated) {
      onJobCreated(jobData.job_id)
      log("Job ID callback executed", jobData.job_id)
    } else {
      logWarn("No job creation callback provided", jobData.job_id)
    }

    // Step 2: Upload file using multipart upload (for all files)
    log(`Starting multipart upload`, jobData.job_id, {
      file_size: file.size,
      filename: file.name,
      flow_step: "upload_start",
    })

    try {
      // Use multipart upload for all files
      await uploadFileViaMultipart(
        file,
        jobData.job_id,
        sessionKey,
        fileKey,
        (progress, fullProgressData) => {
          if (onUploadProgress) {
            onUploadProgress(progress, fullProgressData)
          }
        },
        sendUploadProgress,
      )

      const totalTime = performance.now() - startTime
      log(`Multipart upload completed successfully`, jobData.job_id, {
        filename: file.name,
        total_duration: totalTime,
        file_key: fileKey,
        upload_method: "multipart",
        flow_step: "upload_complete",
      })

      // Return immediately - backend will automatically start processing
      return {
        job_id: jobData.job_id,
        status: "QUEUED", // Backend will transition to PROCESSING
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)

      // Check if it was a user cancellation or abort
      if (errorMessage.includes("cancelled by user") || errorMessage.includes("Upload aborted")) {
        log("Upload cancelled by user", jobData.job_id)
        throw new Error("Upload cancelled by user")
      }

      // Check if it's an authentication error - reload the page to get a fresh session
      if (errorMessage.includes("Invalid session key") || errorMessage.includes("Unauthorized")) {
        logWarn("Authentication error during upload, reloading page to refresh session", {
          job_id: jobData.job_id,
          error: errorMessage,
        })

        // Clear invalid session
        localStorage.removeItem("mangaconverter_session_key")

        // Reload the page to get fresh session and clean state
        window.location.reload()

        // This won't be reached, but TypeScript needs a return
        return { job_id: jobData.job_id, status: "RELOADING" }
      }

      logError("Multipart upload failed", jobData.job_id, {
        error: errorMessage,
      })
      throw new Error(`Upload failed: ${errorMessage}`)
    }
  } finally {
    // Always remove the file from active jobs tracking when done
    activeJobs.delete(fileKey)
    log("File removed from active jobs tracking", {
      filename: file.name,
      file_key: fileKey,
      remaining_active_jobs: activeJobs.size,
    })
  }
}
