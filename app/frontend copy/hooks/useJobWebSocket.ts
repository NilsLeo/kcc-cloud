import { useEffect, useRef, useState, useCallback } from 'react'
import { io, Socket } from 'socket.io-client'
import { log, logError, logWarn, logDebug } from '@/lib/logger'

export interface JobStatus {
  job_id: string
  status: string
  upload_progress_bytes?: number
  upload_progress_formatted?: string
  progress_percent?: number
  projected_eta?: number
  elapsed_seconds?: number
  remaining_seconds?: number
  download_url?: string
  output_filename?: string
  input_filename?: string
  output_file_size?: number
  output_file_size_formatted?: string
  input_file_size?: number
  input_file_size_formatted?: string
  actual_duration?: number
  error?: string
}

type JobStatusCallback = (status: JobStatus) => void

interface UseJobWebSocketReturn {
  connected: boolean
  subscribeToJob: (jobId: string, callback: JobStatusCallback) => void
  unsubscribeFromJob: (jobId: string) => void
  sendUploadProgress: (jobId: string, bytesUploaded: number) => void
  socket: Socket | null
}

export function useJobWebSocket(apiUrl: string): UseJobWebSocketReturn {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [connected, setConnected] = useState(false)
  const subscriptions = useRef<Map<string, JobStatusCallback>>(new Map())
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10

  useEffect(() => {
    log(`[WebSocket] Initializing connection to ${apiUrl}`)

    // Create WebSocket connection
    const newSocket = io(apiUrl, {
      transports: ['websocket', 'polling'], // Try WebSocket first, fallback to polling
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: maxReconnectAttempts,
      timeout: 20000,
    })

    newSocket.on('connect', () => {
      log('[WebSocket] Connected successfully')
      setConnected(true)
      reconnectAttempts.current = 0

      // Resubscribe to all jobs after reconnection
      subscriptions.current.forEach((callback, jobId) => {
        log(`[WebSocket] Resubscribing to job ${jobId} after reconnection`)
        newSocket.emit('subscribe_job', { job_id: jobId })
      })
    })

    newSocket.on('disconnect', (reason) => {
      log(`[WebSocket] Disconnected: ${reason}`)
      setConnected(false)
    })

    newSocket.on('connected', (data) => {
      log('[WebSocket] Server acknowledged connection:', data.message)
    })

    newSocket.on('job_status', (data: JobStatus) => {
      log('[WebSocket] Received job status update:', data)

      // Call registered callback for this job
      const callback = subscriptions.current.get(data.job_id)
      if (callback) {
        callback(data)
      } else {
        logWarn(`[WebSocket] Received status for unsubscribed job: ${data.job_id}`)
      }
    })

    newSocket.on('error', (error) => {
      logError('[WebSocket] Error:', error)
      // If backend reports job not found during early subscribe, retry shortly
      try {
        const msg = typeof error === 'string' ? error : error?.message
        if (msg && typeof msg === 'string' && msg.toLowerCase().includes('job') && msg.toLowerCase().includes('not found')) {
          // Attempt to resubscribe to any jobs after a short delay
          setTimeout(() => {
            subscriptions.current.forEach((_, jobId) => {
              log(`[WebSocket] Retry subscribing to job ${jobId}`)
              newSocket.emit('subscribe_job', { job_id: jobId })
            })
          }, 1500)
        }
      } catch {}
    })

    newSocket.on('reconnect_attempt', (attemptNumber) => {
      reconnectAttempts.current = attemptNumber
      log(`[WebSocket] Reconnection attempt ${attemptNumber}/${maxReconnectAttempts}`)
    })

    newSocket.on('reconnect_failed', () => {
      logError('[WebSocket] Reconnection failed after maximum attempts')
    })

    // Network status listeners
    if (typeof window !== 'undefined') {
      const handleOnline = () => {
        log('[WebSocket] Network connection restored, reconnecting...')
        if (!newSocket.connected) {
          newSocket.connect()
        }
      }

      const handleOffline = () => {
        log('[WebSocket] Network connection lost')
      }

      window.addEventListener('online', handleOnline)
      window.addEventListener('offline', handleOffline)

      // Cleanup network listeners
      const cleanup = () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
      }

      setSocket(newSocket)

      return () => {
        cleanup()
        log('[WebSocket] Closing connection')
        newSocket.close()
      }
    }

    setSocket(newSocket)

    return () => {
      log('[WebSocket] Closing connection')
      newSocket.close()
    }
  }, [apiUrl])

  const subscribeToJob = useCallback((jobId: string, callback: JobStatusCallback) => {
    if (!socket) {
      logWarn('[WebSocket] Cannot subscribe - socket not initialized')
      return
    }

    log(`[WebSocket] Subscribing to job ${jobId}`)
    subscriptions.current.set(jobId, callback)
    socket.emit('subscribe_job', { job_id: jobId })
  }, [socket])

  const unsubscribeFromJob = useCallback((jobId: string) => {
    if (!socket) {
      logWarn('[WebSocket] Cannot unsubscribe - socket not initialized')
      return
    }

    log(`[WebSocket] Unsubscribing from job ${jobId}`)
    subscriptions.current.delete(jobId)
    socket.emit('unsubscribe_job', { job_id: jobId })
  }, [socket])

  const sendUploadProgress = useCallback((jobId: string, bytesUploaded: number) => {
    if (!socket || !connected) {
      // Silently skip if socket not ready - upload progress is optional
      return
    }

    socket.emit('upload_progress', {
      job_id: jobId,
      bytes_uploaded: bytesUploaded,
    })
  }, [socket, connected])

  return {
    connected,
    subscribeToJob,
    unsubscribeFromJob,
    sendUploadProgress,
    socket,
  }
}
