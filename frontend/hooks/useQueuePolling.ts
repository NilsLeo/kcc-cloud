import { useState, useEffect, useCallback, useRef } from 'react'
import { io, Socket } from 'socket.io-client'
import { getSessionKey, removeSessionKey, ensureSession } from '@/lib/session'
import { useSession as useSessionManager } from './use-session'

export interface QueueJob {
  job_id: string
  filename: string // input filename
  output_filename?: string // output filename (only present for COMPLETE jobs)
  status: 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'ERRORED' | 'CANCELLED'
  device_profile: string
  file_size: number
  output_file_size?: number // output file size (only present for COMPLETE jobs)
  is_dismissed?: boolean // whether a COMPLETE job has been dismissed
  dismissed_at?: string // ISO timestamp if dismissed
  completed_at?: string // ISO timestamp when job completed
  worker_download_speed_mbps?: number // Worker download speed in Mbps (only present for QUEUED jobs)
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
 * Hook to receive queue status updates via WebSocket
 *
 * Uses WebSocket push notifications for real-time updates
 * Backend broadcasts complete job state for session whenever any job updates
 *
 * @param _interval - Unused, kept for API compatibility
 * @param enabled - Whether updates are enabled (default: true)
 */
export function useQueuePolling(
  _interval = 30000, // Unused parameter, kept for backward compatibility
  enabled = true
) {
  const IS_DEV = process.env.NODE_ENV !== 'production'
  const { isLoading: sessionLoading, sessionKey } = useSessionManager()
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [isConnecting, setIsConnecting] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const socketRef = useRef<Socket | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8060'

  // WebSocket connection management
  useEffect(() => {
    if (!enabled || sessionLoading) {
      return
    }

    if (!sessionKey) {
      if (IS_DEV) console.log('[WEBSOCKET] No session key, skipping connection')
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
      auth: {
        session_key: sessionKey
      }
    })

    socketRef.current = socket

    // Connection established
    socket.on('connect', () => {
      if (IS_DEV) console.log('[WEBSOCKET] Connected with socket ID:', socket.id)
      setIsConnecting(false)
      setError(null)

      // Subscribe to session updates
      if (IS_DEV) console.log('[WEBSOCKET] Subscribing to session:', sessionKey.substring(0, 8) + '...')
      socket.emit('subscribe_session', { session_key: sessionKey })
    })

    // Receive session updates
    socket.on('session_update', (data: QueueStatus) => {
      if (IS_DEV) console.log(`[WEBSOCKET] Received session update: ${data.jobs?.length || 0} jobs`)
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
  }, [enabled, sessionLoading, API_BASE_URL, sessionKey])

  // Manual refresh function
  const refresh = useCallback(() => {
    if (socketRef.current?.connected) {
      const sessionKey = getSessionKey()
      if (sessionKey) {
        if (IS_DEV) console.log('[WEBSOCKET] Requesting manual refresh')
        socketRef.current.emit('request_session_status', { session_key: sessionKey })
      }
    }
  }, [])

  return {
    queueStatus,
    isPolling: isConnecting,
    error,
    refresh,
  }
}
