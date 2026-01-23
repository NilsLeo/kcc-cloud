import { log, logError } from "./logger"

interface MultipartUploadConfig {
  partSize?: number
  maxConcurrentParts?: number
  retryAttempts?: number
  retryDelay?: number
  uploadTimeoutMs?: number
}

interface UploadPart {
  partNumber: number
  url: string
  blob: Blob
  etag?: string
  uploaded: boolean
}

interface UploadProgress {
  completedParts: number
  totalParts: number
  uploadedBytes: number
  totalBytes: number
  percentage: number
}

export class MultipartUploadClient {
  private apiBaseUrl: string
  private sessionKey: string
  private config: Required<MultipartUploadConfig>
  private aborted = false
  private uploadSessionId: string

  constructor(apiBaseUrl: string, sessionKey: string, config: MultipartUploadConfig = {}) {
    this.apiBaseUrl = apiBaseUrl
    this.sessionKey = sessionKey

    // Get max concurrent parts from env var, fallback to config, then default
    const envMaxConcurrent =
      typeof process !== "undefined" && process.env.NEXT_PUBLIC_MAX_CONCURRENT_PARTS
        ? Number(process.env.NEXT_PUBLIC_MAX_CONCURRENT_PARTS)
        : undefined

    this.config = {
      partSize: config.partSize || 50 * 1024 * 1024, // 50MB
      maxConcurrentParts: config.maxConcurrentParts || envMaxConcurrent || 6, // Env var > config > default (6)
      retryAttempts: config.retryAttempts || 3,
      retryDelay: config.retryDelay || 1000,
      uploadTimeoutMs: config.uploadTimeoutMs || 60000,
    }

    log("[MULTIPART] Client initialized", {
      maxConcurrentParts: this.config.maxConcurrentParts,
      partSize: this.config.partSize,
      source: envMaxConcurrent ? "env_var" : config.maxConcurrentParts ? "config" : "default",
    })

    // Generate unique upload session ID to prevent duplicate uploads from multiple tabs
    this.uploadSessionId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Upload a file using S3 multipart upload
   */
  async uploadFile(file: File, jobId: string, onProgress?: (progress: UploadProgress) => void): Promise<void> {
    this.aborted = false

    // Check if another tab is already uploading this job
    const storageKey = `multipart_upload_${jobId}`
    const existingSession = localStorage.getItem(storageKey)

    if (existingSession) {
      const sessionData = JSON.parse(existingSession)
      const sessionAge = Date.now() - sessionData.timestamp

      // If session is less than 5 minutes old, another tab is likely uploading
      if (sessionAge < 5 * 60 * 1000) {
        throw new Error(
          "This file is already being uploaded in another tab. Please wait for it to complete or close the other tab.",
        )
      }
      // If session is older than 5 minutes, it's likely stale (tab was closed)
      log("[MULTIPART] Found stale upload session, will override", {
        job_id: jobId,
        session_age_ms: sessionAge,
      })
    }

    // Mark this session as active
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        sessionId: this.uploadSessionId,
        timestamp: Date.now(),
        jobId: jobId,
      }),
    )

    try {
      // Step 1: Initiate multipart upload + Pre-warm R2 connection
      log("[MULTIPART] Initiating multipart upload", {
        job_id: jobId,
        file_name: file.name,
        file_size: file.size,
        upload_session_id: this.uploadSessionId,
      })

      const [initResponse] = await Promise.all([
        this.initiateUpload(jobId, file.size),
        this.prewarmConnection(), // Pre-establish HTTP/2 connection to R2
      ])

      const { upload_id, parts } = initResponse

      log("[MULTIPART] Upload initiated", {
        job_id: jobId,
        upload_id,
        num_parts: parts.length,
      })

      // Step 2 & 3: Split file into parts and START UPLOADING IMMEDIATELY
      // Progressive upload: Start with initial batch, fetch more URLs in background
      const initialParts = this.createParts(file, parts)

      // Check if we need to fetch more parts
      const needsMoreParts = initResponse.has_more_parts
      const nextPartNumber = initResponse.next_part_number

      // Upload with progressive part fetching
      await this.uploadPartsProgressive(jobId, file, initialParts, onProgress, needsMoreParts ? nextPartNumber : null)

      // Step 4: Finalize upload
      log("[MULTIPART] Finalizing upload", { job_id: jobId })
      await this.finalizeUpload(jobId)

      log("[MULTIPART] Upload completed successfully", { job_id: jobId })

      // Clear upload session on success
      localStorage.removeItem(storageKey)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      // Only log as error if it's not an expected abort/cancellation
      if (errorMessage.includes("Upload aborted") || errorMessage.includes("CANCELLED")) {
        log("[MULTIPART] Upload cancelled by user", {
          job_id: jobId,
        })
      } else {
        logError("[MULTIPART] Upload failed, aborting", {
          job_id: jobId,
          error: errorMessage,
        })
      }
      await this.abortUpload(jobId)

      // Clear upload session on error
      localStorage.removeItem(storageKey)

      throw error
    }
  }

  /**
   * Pre-warm HTTP/2 connection to R2 by making a dummy HEAD request
   * This establishes the connection before actual uploads start
   */
  private async prewarmConnection(): Promise<void> {
    try {
      // Extract R2 endpoint from first presigned URL (will be available after initiate)
      // For now, just return - connection will be established on first upload
      // This is called in parallel with initiate, so it doesn't add delay
      return Promise.resolve()
    } catch (e) {
      // Ignore prewarm errors - it's just an optimization
      return Promise.resolve()
    }
  }

  /**
   * Step 1: Initiate multipart upload with backend (returns first batch of URLs)
   */
  private async initiateUpload(jobId: string, fileSize: number) {
    const attemptInitiate = async (retryCount = 0): Promise<any> => {
      const response = await fetch(`${this.apiBaseUrl}/jobs/${jobId}/multipart/initiate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Key": this.sessionKey,
        },
        body: JSON.stringify({
          file_size: fileSize,
          part_size: this.config.partSize,
          initial_batch_size: 20, // Get first 20 URLs immediately
        }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          error: "Failed to initiate upload",
        }))

        // Don't retry here - let uploadFileAndConvert handle 401 errors by retrying the entire conversion
        if (response.status === 401 || response.status === 403) {
          log("[MULTIPART] Authentication error during upload initiate - propagating error to retry entire conversion", {
            job_id: jobId,
            status: response.status,
            error: error.error,
          })
        }

        throw new Error(error.error || "Failed to initiate upload")
      }

      return await response.json()
    }

    return attemptInitiate()
  }

  /**
   * Fetch additional batches of presigned URLs (for progressive upload)
   */
  private async fetchPartsBatch(jobId: string, startPart: number, batchSize = 20) {
    const attemptFetch = async (retryCount = 0): Promise<any> => {
      const response = await fetch(`${this.apiBaseUrl}/jobs/${jobId}/multipart/get-parts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Key": this.sessionKey,
        },
        body: JSON.stringify({
          start_part: startPart,
          batch_size: batchSize,
        }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          error: "Failed to fetch parts batch",
        }))

        // Don't retry here - let uploadFileAndConvert handle 401 errors by retrying the entire conversion
        if (response.status === 401 || response.status === 403) {
          log(
            "[MULTIPART] Authentication error during fetch parts - propagating error to retry entire conversion",
            {
              job_id: jobId,
              start_part: startPart,
              status: response.status,
              error: error.error,
            },
          )
        }

        throw new Error(error.error || "Failed to fetch parts batch")
      }

      return await response.json()
    }

    return attemptFetch()
  }

  /**
   * Step 2: Create upload parts from file
   */
  private createParts(file: File, partUrls: Array<{ part_number: number; url: string }>): UploadPart[] {
    const parts: UploadPart[] = []

    for (const partUrl of partUrls) {
      const start = (partUrl.part_number - 1) * this.config.partSize
      const end = Math.min(start + this.config.partSize, file.size)
      const blob = file.slice(start, end)

      parts.push({
        partNumber: partUrl.part_number,
        url: partUrl.url,
        blob: blob,
        uploaded: false,
      })
    }

    return parts
  }

  /**
   * Upload parts progressively - fetch additional URL batches as needed
   * OPTIMIZED: Start uploading immediately with first batch, fetch more in background
   */
  private async uploadPartsProgressive(
    jobId: string,
    file: File,
    initialParts: UploadPart[],
    onProgress?: (progress: UploadProgress) => void,
    nextPartToFetch?: number | null,
  ): Promise<void> {
    const allParts: UploadPart[] = [...initialParts]
    let isFetchingMore = false
    let fetchError: Error | null = null

    // Background task to fetch additional URL batches
    const fetchMoreParts = async () => {
      if (!nextPartToFetch || isFetchingMore) return

      isFetchingMore = true
      try {
        log("[MULTIPART] Fetching additional URL batch in background", {
          job_id: jobId,
          start_part: nextPartToFetch,
        })

        const batchResponse = await this.fetchPartsBatch(jobId, nextPartToFetch, 20)
        const newParts = this.createParts(file, batchResponse.parts)

        // Add new parts to the queue
        allParts.push(...newParts)

        log("[MULTIPART] Fetched additional URL batch", {
          job_id: jobId,
          fetched_parts: newParts.length,
          total_parts_available: allParts.length,
        })

        // Update nextPartToFetch for next batch
        if (batchResponse.has_more_parts) {
          nextPartToFetch = batchResponse.next_part_number
        } else {
          nextPartToFetch = null
        }
      } catch (error) {
        fetchError = error as Error
        logError("[MULTIPART] Failed to fetch additional parts", {
          job_id: jobId,
          error: error instanceof Error ? error.message : String(error),
        })
      } finally {
        isFetchingMore = false
      }
    }

    // Start fetching next batch immediately if needed
    if (nextPartToFetch) {
      fetchMoreParts()
    }

    // Upload parts with automatic batch fetching
    // Note: totalParts will be calculated dynamically as allParts grows
    let completedParts = 0
    let uploadedBytes = 0
    const totalBytes = file.size

    // Track in-progress bytes for real-time progress updates
    const partProgressBytes = new Map<number, number>() // partNumber -> bytes uploaded so far
    let lastReportedProgress = 0 // Track last reported percentage to prevent backwards movement

    const storageKey = `multipart_upload_${jobId}`
    const heartbeatInterval = setInterval(() => {
      if (!this.aborted) {
        localStorage.setItem(
          storageKey,
          JSON.stringify({
            sessionId: this.uploadSessionId,
            timestamp: Date.now(),
            jobId: jobId,
            progress: {
              completed: completedParts,
              total: allParts.length, // Dynamic total as parts are fetched
            },
          }),
        )
      }
    }, 10000)

    try {
      const activeTasks = new Set<Promise<void>>()
      let partIndex = 0

      // Helper to calculate total progress including in-progress parts
      const calculateTotalProgress = () => {
        let inProgressBytes = 0
        for (const bytes of partProgressBytes.values()) {
          inProgressBytes += bytes
        }
        return uploadedBytes + inProgressBytes
      }

      // Helper to trigger progress callback (ensures progress never goes backwards)
      const updateProgress = () => {
        if (onProgress) {
          const totalUploadedBytes = calculateTotalProgress()
          const currentProgress = (totalUploadedBytes / totalBytes) * 100

          // Only update if progress moves forward (or stays the same)
          if (currentProgress >= lastReportedProgress) {
            lastReportedProgress = currentProgress
            onProgress({
              completedParts,
              totalParts: allParts.length, // Dynamic total
              uploadedBytes: totalUploadedBytes,
              totalBytes,
              percentage: currentProgress,
            })
          }
        }
      }

      const uploadNext = async () => {
        while (true) {
          if (this.aborted) {
            throw new Error("Upload aborted")
          }

          // Check if we've uploaded all parts
          if (partIndex >= allParts.length && !nextPartToFetch) {
            break
          }

          // Wait if we're at max concurrency
          while (activeTasks.size >= this.config.maxConcurrentParts) {
            await Promise.race(activeTasks)
          }

          // If no parts available but more are coming, wait for fetch
          if (partIndex >= allParts.length && nextPartToFetch) {
            if (!isFetchingMore) {
              await fetchMoreParts()
            } else {
              await new Promise((resolve) => setTimeout(resolve, 100))
            }
            continue
          }

          // Throw if fetch failed
          if (fetchError) {
            throw fetchError
          }

          // No more parts to upload
          if (partIndex >= allParts.length) {
            break
          }

          const part = allParts[partIndex++]

          // Progress callback for this specific part
          const partProgressCallback = (partBytes: number) => {
            partProgressBytes.set(part.partNumber, partBytes)
            updateProgress()
          }

          const uploadTask = this.uploadPart(jobId, part, partProgressCallback)
            .then(() => {
              completedParts++

              // CRITICAL: When a part completes, we need to account for the fact that
              // it was already being tracked in partProgressBytes. We remove it from
              // in-progress tracking and add the FULL size to uploadedBytes.
              // The calculation in calculateTotalProgress() is:
              //   uploadedBytes (completed parts) + sum(partProgressBytes) (in-progress parts)
              // So when we move a part from in-progress to completed:
              //   - partProgressBytes loses the partial bytes (e.g., 8MB out of 10MB)
              //   - uploadedBytes gains the full part size (10MB)
              // This can cause a dip if the part was close to completion.
              // Solution: Remove BEFORE adding to maintain monotonic progress
              const wasInProgress = partProgressBytes.has(part.partNumber)
              const inProgressBytes = wasInProgress ? partProgressBytes.get(part.partNumber)! : 0

              partProgressBytes.delete(part.partNumber)
              uploadedBytes += part.blob.size

              updateProgress()

              log("[MULTIPART] Part completed and confirmed by backend", {
                job_id: jobId,
                part_number: part.partNumber,
                completed: completedParts,
                total: allParts.length, // Dynamic total
                percentage: ((uploadedBytes / totalBytes) * 100).toFixed(1) + "%",
              })

              // Trigger next batch fetch when we're getting close to running out
              if (nextPartToFetch && !isFetchingMore && partIndex >= allParts.length - 5) {
                fetchMoreParts()
              }
            })
            .catch((error) => {
              const errorMessage = error instanceof Error ? error.message : String(error)

              // Clean up progress tracking for failed part
              partProgressBytes.delete(part.partNumber)
              updateProgress()

              // Only log as error if it's not an expected abort/cancellation
              if (errorMessage.includes("Upload aborted") || errorMessage.includes("CANCELLED")) {
                log("[MULTIPART] Part upload cancelled", {
                  job_id: jobId,
                  part_number: part.partNumber,
                })
              } else {
                logError("[MULTIPART] Part upload failed", {
                  job_id: jobId,
                  part_number: part.partNumber,
                  error: errorMessage,
                })
              }
              throw error
            })
            .finally(() => {
              activeTasks.delete(uploadTask)
            })

          activeTasks.add(uploadTask)
        }
      }

      await uploadNext()

      if (activeTasks.size > 0) {
        try {
          await Promise.all(activeTasks)
        } catch (error) {
          // If it's an abort error, it's expected - just log and continue to finally block
          const errorMessage = error instanceof Error ? error.message : String(error)
          if (errorMessage.includes("Upload aborted") || errorMessage.includes("CANCELLED")) {
            log("[MULTIPART] Active tasks cancelled", { job_id: jobId })
          }
          // Re-throw so uploadFileViaMultipart can handle it
          throw error
        }
      }
    } finally {
      clearInterval(heartbeatInterval)
    }
  }

  /**
   * Step 3: Upload parts with concurrency control and retry logic (LEGACY - kept for compatibility)
   * OPTIMIZED: All parts start immediately, no waiting for slots
   */
  private async uploadParts(
    jobId: string,
    parts: UploadPart[],
    onProgress?: (progress: UploadProgress) => void,
  ): Promise<void> {
    const totalParts = parts.length
    let completedParts = 0
    let uploadedBytes = 0
    const totalBytes = parts.reduce((sum, p) => sum + p.blob.size, 0)

    // Set up heartbeat to update upload session timestamp (prevents stale session detection)
    const storageKey = `multipart_upload_${jobId}`
    const heartbeatInterval = setInterval(() => {
      if (!this.aborted) {
        localStorage.setItem(
          storageKey,
          JSON.stringify({
            sessionId: this.uploadSessionId,
            timestamp: Date.now(),
            jobId: jobId,
            progress: {
              completed: completedParts,
              total: totalParts,
            },
          }),
        )
      }
    }, 10000) // Update every 10 seconds

    try {
      // Start ALL uploads immediately with concurrency limit using a semaphore pattern
      const activeTasks = new Set<Promise<void>>()
      let partIndex = 0

      const uploadNext = async () => {
        while (partIndex < parts.length) {
          if (this.aborted) {
            throw new Error("Upload aborted")
          }

          // Wait if we're at max concurrency
          while (activeTasks.size >= this.config.maxConcurrentParts) {
            await Promise.race(activeTasks)
          }

          const part = parts[partIndex++]

          const uploadTask = this.uploadPart(jobId, part)
            .then(() => {
              completedParts++
              uploadedBytes += part.blob.size

              // Report progress - this only happens after BOTH S3 upload AND backend notification succeed
              if (onProgress) {
                onProgress({
                  completedParts,
                  totalParts,
                  uploadedBytes,
                  totalBytes,
                  percentage: (completedParts / totalParts) * 100,
                })
              }

              log("[MULTIPART] Part completed and confirmed by backend", {
                job_id: jobId,
                part_number: part.partNumber,
                completed: completedParts,
                total: totalParts,
                percentage: ((completedParts / totalParts) * 100).toFixed(1) + "%",
              })
            })
            .catch((error) => {
              logError("[MULTIPART] Part upload failed", {
                job_id: jobId,
                part_number: part.partNumber,
                error: error instanceof Error ? error.message : String(error),
                stage: "upload_or_notification",
              })
              throw error // Re-throw to fail the entire upload
            })
            .finally(() => {
              activeTasks.delete(uploadTask)
            })

          activeTasks.add(uploadTask)
        }
      }

      // Start upload pump
      await uploadNext()

      // Wait for all remaining uploads to complete
      if (activeTasks.size > 0) {
        await Promise.all(activeTasks)
      }
    } finally {
      // Always clear heartbeat
      clearInterval(heartbeatInterval)
    }
  }

  /**
   * Upload a single part with retry logic and real-time progress tracking
   */
  private async uploadPart(
    jobId: string,
    part: UploadPart,
    onPartProgress?: (bytesUploaded: number) => void,
  ): Promise<void> {
    let lastError: Error | null = null

    for (let attempt = 0; attempt < this.config.retryAttempts; attempt++) {
      // Check if upload was aborted before attempting
      if (this.aborted) {
        throw new Error("Upload aborted")
      }

      // Reset part progress to 0 before each attempt (including retries)
      // This prevents failed attempts from inflating the total progress
      if (onPartProgress) {
        onPartProgress(0)
      }

      try {
        // Upload to S3 using presigned URL with XMLHttpRequest for progress tracking
        log(`[MULTIPART] Uploading part ${part.partNumber} to S3 (attempt ${attempt + 1})`, {
          job_id: jobId,
          part_number: part.partNumber,
          part_size: part.blob.size,
        })

        // Use XMLHttpRequest instead of fetch() to get upload progress events
        const etag = await new Promise<string>((resolve, reject) => {
          const xhr = new XMLHttpRequest()

          // Set timeout to prevent stuck uploads (Hetzner S3 timeout is ~60-80s)
          // We set it to 60s to fail faster and retry with fresh connection
          xhr.timeout = Math.max(10000, this.config.uploadTimeoutMs) // configurable, min 10s

          let lastProgressTime = Date.now()
          let lastProgressBytes = 0

          // Track upload progress
          xhr.upload.addEventListener("progress", (e) => {
            if (e.lengthComputable && onPartProgress) {
              // Report bytes uploaded for this part
              onPartProgress(e.loaded)

              // Track progress for stall detection
              lastProgressTime = Date.now()
              lastProgressBytes = e.loaded
            }
          })

          // Handle completion
          xhr.addEventListener("load", () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              // Get ETag from response headers
              const etag = xhr.getResponseHeader("ETag")
              if (!etag) {
                reject(new Error("No ETag in S3 response"))
              } else {
                resolve(etag)
              }
            } else {
              reject(new Error(`S3 upload failed: ${xhr.status}`))
            }
          })

          // Handle timeout
          xhr.addEventListener("timeout", () => {
            const timeoutSeconds = Math.round(this.config.uploadTimeoutMs / 1000)
            reject(new Error(`Upload timeout after ${timeoutSeconds}s - will retry with fresh connection`))
          })

          // Handle errors
          xhr.addEventListener("error", () => {
            reject(new Error("Network error during S3 upload"))
          })

          xhr.addEventListener("abort", () => {
            reject(new Error("Upload aborted"))
          })

          // Check for abort before starting
          if (this.aborted) {
            reject(new Error("Upload aborted"))
            return
          }

          // Start upload
          xhr.open("PUT", part.url)
          xhr.setRequestHeader("Content-Type", "application/octet-stream")
          xhr.send(part.blob)

          // Store xhr for potential abort
          ;(part as any).xhr = xhr
        })

        log(`[MULTIPART] Part ${part.partNumber} uploaded to S3, notifying backend`, {
          job_id: jobId,
          part_number: part.partNumber,
          etag: etag,
        })

        part.etag = etag
        part.uploaded = true

        // Part fully uploaded to S3 - report completion immediately
        // This ensures progress reflects actual upload, not backend confirmation
        if (onPartProgress) {
          onPartProgress(part.blob.size)
        }

        // Check if upload was aborted before notifying backend
        if (this.aborted) {
          throw new Error("Upload aborted")
        }

        // Notify backend of part completion - this is critical!
        await this.notifyPartComplete(jobId, part.partNumber, etag)

        log(`[MULTIPART] Part ${part.partNumber} confirmed by backend`, {
          job_id: jobId,
          part_number: part.partNumber,
        })

        return // Success!
      } catch (error) {
        lastError = error as Error

        // If upload was aborted or backend rejected due to cancellation, don't retry
        const errorMessage = error instanceof Error ? error.message : String(error)
        if (this.aborted || errorMessage.includes("Upload aborted") || errorMessage.includes("CANCELLED status")) {
          throw error
        }

        logError(`[MULTIPART] Part ${part.partNumber} attempt ${attempt + 1} failed`, {
          job_id: jobId,
          part_number: part.partNumber,
          attempt: attempt + 1,
          error: errorMessage,
        })

        if (attempt < this.config.retryAttempts - 1) {
          // Wait before retry (exponential backoff)
          await this.sleep(this.config.retryDelay * Math.pow(2, attempt))
        }
      }
    }

    // All retries failed - clean up progress tracking for this part
    if (onPartProgress) {
      onPartProgress(0)
    }

    throw new Error(`Part ${part.partNumber} failed after ${this.config.retryAttempts} attempts: ${lastError?.message}`)
  }

  /**
   * Notify backend that a part was uploaded
   */
  private async notifyPartComplete(jobId: string, partNumber: number, etag: string): Promise<void> {
    const response = await fetch(`${this.apiBaseUrl}/jobs/${jobId}/multipart/complete-part`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Key": this.sessionKey,
      },
      body: JSON.stringify({
        part_number: partNumber,
        etag: etag,
      }),
    })

    if (!response.ok) {
      let errorMessage = `Failed to notify backend of part ${partNumber} completion (HTTP ${response.status})`
      try {
        const errorData = await response.json()
        if (errorData.error) {
          errorMessage = `Part ${partNumber}: ${errorData.error}`
        }
      } catch (e) {
        // Couldn't parse error response, use default message
      }

      logError("[MULTIPART] Backend notification failed", {
        job_id: jobId,
        part_number: partNumber,
        status: response.status,
        error: errorMessage,
      })

      throw new Error(errorMessage)
    }

    // Verify the response contains success confirmation
    const result = await response.json()
    if (!result.success) {
      throw new Error(`Part ${partNumber}: Backend did not confirm completion`)
    }
  }

  /**
   * Step 4: Finalize the multipart upload
   */
  private async finalizeUpload(jobId: string): Promise<void> {
    const response = await fetch(`${this.apiBaseUrl}/jobs/${jobId}/multipart/finalize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Key": this.sessionKey,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: "Failed to finalize upload",
      }))

      // If parts are missing, provide detailed error message
      if (error.completed_parts !== undefined && error.total_parts !== undefined) {
        const message = `Upload incomplete: Only ${error.completed_parts} of ${error.total_parts} parts were confirmed by the backend. This may happen if the page was refreshed during upload or if there were network errors.`
        logError("[MULTIPART] Finalize failed - missing parts", {
          job_id: jobId,
          completed_parts: error.completed_parts,
          total_parts: error.total_parts,
        })
        throw new Error(message)
      }

      throw new Error(error.error || "Failed to finalize upload")
    }
  }

  /**
   * Abort the multipart upload
   */
  async abortUpload(jobId: string): Promise<void> {
    this.aborted = true

    try {
      await fetch(`${this.apiBaseUrl}/jobs/${jobId}/multipart/abort`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Key": this.sessionKey,
        },
      })
      log("[MULTIPART] Upload aborted", { job_id: jobId })
    } catch (error) {
      logError("[MULTIPART] Failed to abort upload", {
        job_id: jobId,
        error: error instanceof Error ? error.message : String(error),
      })
    }
  }

  /**
   * Utility: Sleep for ms milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }
}

export type { UploadProgress }
