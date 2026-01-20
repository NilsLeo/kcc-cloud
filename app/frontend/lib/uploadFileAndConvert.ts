import { log, logError } from "./logger"

/**
 * FOSS version - Simple direct file upload and conversion
 * No multipart uploads, no S3, just direct POST to backend
 */

export type UploadProgress = {
  completed_parts: number
  total_parts: number
  uploaded_bytes: number
  total_bytes: number
  percentage: number
}

// Track active XHRs by jobId for cancellation
const activeXhrs = new Map<string, XMLHttpRequest>()

// Export function to abort an active upload (simplified for FOSS)
export function abortUpload(jobId: string): boolean {
  try {
    const xhr = activeXhrs.get(jobId)
    if (xhr) {
      xhr.abort()
      activeXhrs.delete(jobId)
      return true
    }
    return false
  } catch {
    return false
  }
}

export async function uploadFileAndConvert(
  file: File,
  jobId: string,
  deviceProfile: string,
  options: Record<string, any>,
  onProgress: (progress: number, fullProgressData?: UploadProgress) => void,
): Promise<{ job_id: string }> {
  log(`[UPLOAD] Starting direct upload for job ${jobId}`, {
    file_name: file.name,
    file_size: file.size,
    device_profile: deviceProfile,
  })

  const formData = new FormData()
  formData.append('file', file)
  formData.append('device_profile', deviceProfile)
  formData.append('job_id', jobId)
  for (const [key, value] of Object.entries(options)) {
    if (value !== undefined && value !== null) formData.append(key, String(value))
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8060'

  return await new Promise<{ job_id: string }>((resolve, reject) => {
    try {
      const xhr = new XMLHttpRequest()
      activeXhrs.set(jobId, xhr)

      xhr.open('POST', `${apiUrl}/jobs`)

      // Upload progress events
      xhr.upload.onprogress = (e: ProgressEvent) => {
        if (!e.lengthComputable) return
        const uploaded = e.loaded
        const total = e.total || file.size
        const pct = Math.max(0, Math.min(100, (uploaded / Math.max(1, total)) * 100))
        onProgress(pct, {
          completed_parts: 0,
          total_parts: 0,
          uploaded_bytes: uploaded,
          total_bytes: total,
          percentage: pct,
        })
      }

      xhr.onerror = () => {
        activeXhrs.delete(jobId)
        reject(new Error('Upload failed'))
      }
      xhr.onabort = () => {
        activeXhrs.delete(jobId)
        reject(new Error('Upload aborted'))
      }

      xhr.onreadystatechange = () => {
        if (xhr.readyState !== XMLHttpRequest.DONE) return
        const status = xhr.status
        try {
          const result = JSON.parse(xhr.responseText || '{}')
          if (status >= 200 && status < 300) {
            log(`[UPLOAD] Upload successful for job ${jobId}`, {
              job_id: result.job_id,
              status: result.status,
            })
            // Ensure final 100% emit
            onProgress(100, {
              completed_parts: 0,
              total_parts: 0,
              uploaded_bytes: file.size,
              total_bytes: file.size,
              percentage: 100,
            })
            activeXhrs.delete(jobId)
            resolve({ job_id: result.job_id })
          } else {
            const msg = result?.error || `Upload failed: ${status}`
            activeXhrs.delete(jobId)
            reject(new Error(msg))
          }
        } catch (err) {
          activeXhrs.delete(jobId)
          reject(new Error(`Upload failed: invalid server response (${status})`))
        }
      }

      xhr.send(formData)
    } catch (err) {
      activeXhrs.delete(jobId)
      logError(`[UPLOAD] Upload failed for job ${jobId}`, { error: err })
      reject(err as any)
    }
  })
}
