"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, FileText, Loader2, X, Clock, ArrowRight, HardDrive, AlertCircle } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { useSession } from "@/hooks/use-session"
import { removeSessionKey, getOrCreateAnonymousSession } from "@/lib/session"

export type UserDownload = {
  job_id: string
  original_filename: string
  converted_filename: string
  device_profile: string
  input_file_size?: number
  output_file_size?: number
  completed_at?: string
  actual_duration?: number
  download_url: string
  download_attempts: number
  session_alias?: string
  session_device?: {
    browser?: string
    os?: string
    device?: string
  }
}

interface MyDownloadsProps {
  limit?: number
}

export function MyDownloads({ limit = 100 }: MyDownloadsProps) {
  // Auto-initialize session for this component since it needs to fetch user data
  const { sessionKey, isLoading: sessionLoading, error: sessionError, isAnonymous } = useSession({ autoInitialize: true })
  const [downloads, setDownloads] = useState<UserDownload[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({})
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    // Wait for session initialization to complete, then fetch downloads
    if (!sessionLoading && sessionKey) {
      console.log('[MyDownloads] Session ready, fetching downloads')
      fetchDownloads()
    }
  }, [sessionLoading, sessionKey])

  const fetchDownloads = async () => {
    try {
      setLoading(true)
      setError(null)

      // Must be logged in (not anonymous)
      if (isAnonymous) {
        setError("Please sign in to view your downloads")
        setLoading(false)
        return
      }

      if (!sessionKey) {
        setError("Failed to get session key")
        setLoading(false)
        return
      }

      console.log('[MyDownloads] Fetching downloads with session key:', sessionKey?.substring(0, 8) + '...')

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"
      const response = await fetch(`${API_BASE_URL}/api/user/downloads?limit=${limit}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Key": sessionKey,
        },
      })

      console.log('[MyDownloads] Response status:', response.status)

      if (!response.ok) {
        const data = await response.json()
        console.error('[MyDownloads] Error response:', data)

        // If we get a 401, the session is invalid - clear it and reload
        if (response.status === 401) {
          console.warn('[MyDownloads] 401 Unauthorized - clearing invalid session')
          removeSessionKey()
          toast.error("Session expired", {
            description: "Please refresh the page to continue.",
          })
          // Trigger page reload after short delay
          setTimeout(() => window.location.reload(), 2000)
          return
        }

        throw new Error(data.error || "Failed to fetch downloads")
      }

      const data = await response.json()
      console.log('[MyDownloads] Received data:', {
        downloads_count: data.downloads?.length || 0,
        total: data.total,
        has_more: data.has_more
      })
      setDownloads(data.downloads || [])
      setTotalCount(data.total || 0)
    } catch (err) {
      console.error("Error fetching downloads:", err)
      setError(err instanceof Error ? err.message : "Failed to fetch downloads")
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (isoString?: string) => {
    if (!isoString) return "Unknown date"
    return new Date(isoString).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return "Unknown size"
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return null

    if (seconds < 60) {
      return `${Math.round(seconds)}s`
    }

    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.round(seconds % 60)

    if (remainingSeconds === 0) {
      return `${minutes}m`
    }

    return `${minutes}m ${remainingSeconds}s`
  }

  const formatDeviceInfo = (sessionDevice?: { browser?: string; os?: string; device?: string }) => {
    if (!sessionDevice) return null
    const parts = []
    if (sessionDevice.browser) parts.push(sessionDevice.browser)
    if (sessionDevice.os) parts.push(sessionDevice.os)
    if (sessionDevice.device) parts.push(sessionDevice.device)
    return parts.join(" • ")
  }

  const downloadFile = async (download: UserDownload) => {
    try {
      setDownloadingFiles((prev) => ({ ...prev, [download.job_id]: true }))

      // Use the presigned URL directly from the API response
      window.location.href = download.download_url
      toast.success(`Downloading ${download.converted_filename}`)
    } catch (error) {
      console.error("Download error:", error)
      toast.error("Download failed", {
        description: error instanceof Error ? error.message : "Failed to download file",
      })
    } finally {
      setTimeout(() => {
        setDownloadingFiles((prev) => ({ ...prev, [download.job_id]: false }))
      }, 1000)
    }
  }

  if (sessionLoading || loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>My Downloads</CardTitle>
          <CardDescription>Loading your converted files...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || sessionError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>My Downloads</CardTitle>
          <CardDescription>Your converted files from all devices</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || sessionError?.message}</AlertDescription>
          </Alert>
          <Button onClick={fetchDownloads} className="mt-4">
            Try Again
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (downloads.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>My Downloads</CardTitle>
          <CardDescription>Your converted files from all devices</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No downloads yet</p>
            <p className="text-sm">Convert some files to see them here!</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>My Downloads</CardTitle>
            <CardDescription>
              {totalCount} converted file{totalCount !== 1 ? "s" : ""} from all your devices
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={fetchDownloads}>
            Refresh
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          <AnimatePresence>
            {downloads.map((download) => (
              <motion.div
                key={download.job_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className="group relative rounded-lg border bg-card hover:bg-accent/50 transition-all duration-200 overflow-hidden"
              >
                <div className="flex items-start gap-4 p-4">
                  {/* File icon */}
                  <div className="p-2.5 rounded-lg bg-primary/10 text-primary shrink-0">
                    <FileText className="h-5 w-5" />
                  </div>

                  {/* File info */}
                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Filename */}
                    <div>
                      <p className="font-semibold text-base truncate">{download.converted_filename}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <span>{formatDate(download.completed_at)}</span>
                        <span>•</span>
                        <Badge variant="secondary" className="text-xs font-normal">
                          {download.device_profile}
                        </Badge>
                      </div>
                    </div>

                    {/* File size and duration info */}
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      {/* File size conversion */}
                      {download.input_file_size && download.output_file_size ? (
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <HardDrive className="h-3.5 w-3.5" />
                          <span className="font-medium">{formatFileSize(download.input_file_size)}</span>
                          <ArrowRight className="h-3 w-3" />
                          <span className="font-medium text-foreground">{formatFileSize(download.output_file_size)}</span>
                        </div>
                      ) : download.output_file_size ? (
                        <div className="flex items-center gap-1.5 text-muted-foreground">
                          <HardDrive className="h-3.5 w-3.5" />
                          <span className="font-medium">{formatFileSize(download.output_file_size)}</span>
                        </div>
                      ) : null}

                      {/* Duration */}
                      {download.actual_duration && (
                        <>
                          <span className="text-muted-foreground">•</span>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Clock className="h-3.5 w-3.5" />
                            <span className="font-medium">{formatDuration(download.actual_duration)}</span>
                          </div>
                        </>
                      )}

                      {/* Device info */}
                      {formatDeviceInfo(download.session_device) && (
                        <>
                          <span className="text-muted-foreground">•</span>
                          <span className="text-xs text-muted-foreground">
                            {formatDeviceInfo(download.session_device)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Download button */}
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      onClick={() => downloadFile(download)}
                      disabled={downloadingFiles[download.job_id]}
                      size="default"
                      className="shadow-sm"
                      aria-label={`Download ${download.converted_filename}`}
                    >
                      {downloadingFiles[download.job_id] ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin mr-2" />
                          Downloading
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-2" />
                          Download
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}
