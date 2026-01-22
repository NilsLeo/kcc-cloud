import { useState, useEffect, useCallback, useRef } from 'react'
import { io, Socket } from 'socket.io-client'

export interface QueueJob {
  job_id: string
  filename: string
  output_filename?: string
  status: 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETE' | 'ERRORED' | 'CANCELLED'
  device_profile: string
  file_size: number
  output_file_size?: number
  completed_at?: string
  processing_at?: string
  eta_at?: string
  upload_progress?: {
    completed_parts: number
    total_parts: number
    uploaded_bytes: number
    total_bytes: number
    percentage: number
  }
  queue_position?: number
}

export interface QueueStatus {
  jobs: QueueJob[]
  total: number
  timestamp: string
}

// WebSocket-only queue updates (no HTTP polling)
export function useQueueUpdates(enabled = true) {
  const IS_DEV = process.env.NODE_ENV !== 'production'
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [isConnecting, setIsConnecting] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const socketRef = useRef<Socket | null>(null)
  // For WebSocket, prefer same-origin unless NEXT_PUBLIC_SOCKET_URL is set
  // Using NEXT_PUBLIC_API_URL (e.g. "/api") would incorrectly target "/api/socket.io"
  // which isn't upgraded by nginx. So default to same-origin Socket.IO endpoint.
  const SOCKET_URL = (process.env.NEXT_PUBLIC_SOCKET_URL || '').trim()

  useEffect(() => {
    if (!enabled) return

    if (IS_DEV) console.log('[WEBSOCKET] Connecting to', SOCKET_URL || '(same-origin)')
    setIsConnecting(true)

    const socket = io(SOCKET_URL || undefined, {
      // Explicitly set path to avoid "/api/socket.io" when API base is "/api"
      path: '/socket.io',
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      timeout: 10000,
    })

    socketRef.current = socket

    socket.on('connect', () => {
      if (IS_DEV) console.log('[WEBSOCKET] Connected:', socket.id)
      setIsConnecting(false)
      setError(null)
      socket.emit('subscribe_queue')
    })

    socket.on('queue_update', (data: QueueStatus) => {
      if (IS_DEV) {
        console.log(`[WEBSOCKET] queue_update: ${data.jobs?.length || 0} jobs`)
        try {
          const brief = (data.jobs || []).map((j: any) => ({
            job_id: j.job_id,
            status: j.status,
            filename: j.filename,
            file_size: j.file_size,
            output_file_size: j.output_file_size,
          }))
          // Use table for readability in devtools
          if ((console as any).table) (console as any).table(brief)
          else console.log('[WEBSOCKET] queue_update brief:', brief)
        } catch {}
      }
      setQueueStatus(data)
    })

    socket.on('connect_error', (err) => {
      console.error('[WEBSOCKET] Connection error:', err.message)
      setIsConnecting(true)
      setError(`WebSocket connection error: ${err.message}`)
    })

    socket.on('disconnect', (reason) => {
      if (IS_DEV) console.warn('[WEBSOCKET] Disconnected:', reason)
      setIsConnecting(true)
    })

    socket.on('error', (errorData: any) => {
      console.error('[WEBSOCKET] Server error:', errorData)
      setError(errorData.message || 'WebSocket error')
    })

    return () => {
      if (IS_DEV) console.log('[WEBSOCKET] Disconnecting')
      socket.disconnect()
      socketRef.current = null
    }
  }, [enabled, API_BASE_URL, IS_DEV])

  const refresh = useCallback(() => {
    if (socketRef.current?.connected) {
      if (IS_DEV) console.log('[WEBSOCKET] Requesting manual refresh')
      socketRef.current.emit('request_queue_status')
    }
  }, [IS_DEV])

  return {
    queueStatus,
    isConnecting,
    error,
    refresh,
  }
}
