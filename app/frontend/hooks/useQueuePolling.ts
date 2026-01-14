import { useState, useEffect, useCallback, useRef } from 'react'
import { io, Socket } from 'socket.io-client'

export interface QueueJob {
  job_id: string
  filename: string // input filename
  output_filename?: string // output filename (only present for COMPLETE jobs)
  status: 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'ERRORED' | 'CANCELLED'
  device_profile: string
  file_size: number
  output_file_size?: number // output file size (only present for COMPLETE jobs)
  completed_at?: string // ISO timestamp when job completed
  upload_progress?: {
    completed_parts: number
    total_parts: number
    uploaded_bytes: number
    total_bytes: number
    percentage: number
  }
  processing_progress?: {
    elapsed_seconds: number
    remaining_seconds: number
    projected_eta: number
    progress_percent: number
  }
  queue_position?: number
}

export interface QueueStatus {
  jobs: QueueJob[]
  total: number
  timestamp: string
}

/**
 * FOSS version - WebSocket updates for queue status
 * No authentication, broadcasts to all clients
 *
 * @param _interval - Unused, kept for API compatibility
 * @param enabled - Whether updates are enabled (default: true)
 */
export function useQueuePolling(
  _interval = 30000, // Unused parameter, kept for backward compatibility
  enabled = true
) {
  const IS_DEV = process.env.NODE_ENV !== 'production'
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [isConnecting, setIsConnecting] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const socketRef = useRef<Socket | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8060'

  // WebSocket connection management
  useEffect(() => {
    if (!enabled) {
      return
    }

    if (IS_DEV) console.log('[WEBSOCKET] Connecting to', API_BASE_URL)
    setIsConnecting(true)

    // Create Socket.IO connection
    const socket = io(API_BASE_URL, {
      transports: ['websocket'], // WebSocket only
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity, // Keep trying to reconnect
      timeout: 10000,
    })

    socketRef.current = socket

    // Connection established
    socket.on('connect', () => {
      if (IS_DEV) console.log('[WEBSOCKET] Connected with socket ID:', socket.id)
      setIsConnecting(false)
      setError(null)

      // Subscribe to queue updates
      if (IS_DEV) console.log('[WEBSOCKET] Subscribing to queue updates')
      socket.emit('subscribe_queue')
    })

    // Receive queue updates
    socket.on('queue_update', (data: QueueStatus) => {
      if (IS_DEV) console.log(`[WEBSOCKET] Received queue update: ${data.jobs?.length || 0} jobs`)
      setQueueStatus(data)
    })

    // Connection errors
    socket.on('connect_error', (err) => {
      console.error('[WEBSOCKET] Connection error:', err.message)
      setIsConnecting(true)
      setError(`WebSocket connection error: ${err.message}`)
    })

    // Disconnected
    socket.on('disconnect', (reason) => {
      if (IS_DEV) console.warn('[WEBSOCKET] Disconnected:', reason)
      setIsConnecting(true)
    })

    // Error from server
    socket.on('error', (errorData: any) => {
      console.error('[WEBSOCKET] Server error:', errorData)
      setError(errorData.message || 'WebSocket error')
    })

    // Cleanup
    return () => {
      if (IS_DEV) console.log('[WEBSOCKET] Disconnecting')
      socket.disconnect()
      socketRef.current = null
    }
  }, [enabled, API_BASE_URL, IS_DEV])

  // Manual refresh function
  const refresh = useCallback(() => {
    if (socketRef.current?.connected) {
      if (IS_DEV) console.log('[WEBSOCKET] Requesting manual refresh')
      socketRef.current.emit('request_queue_status')
    }
  }, [IS_DEV])

  return {
    queueStatus,
    isPolling: isConnecting,
    error,
    refresh,
  }
}
