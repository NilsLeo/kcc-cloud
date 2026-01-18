"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileText, RefreshCw } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle } from "lucide-react"
import mockData from "@/lib/mock-data.json"
import type { UserDownload } from "@/types/user-download"
import { FileConversionCard } from "./file-conversion-card"

const getStatusStages = (currentStatus: string, hasError = false) => {
  if (hasError) {
    return ["UPLOADING", "PROCESSING", "ERRORRED"] as const
  }
  if (currentStatus === "QUEUED") {
    return ["UPLOADING", "QUEUED", "COMPLETE"] as const
  }
  return ["UPLOADING", "PROCESSING", "COMPLETE"] as const
}

interface MyDownloadsProps {
  limit?: number
}

export function MyDownloads({ limit = 100 }: MyDownloadsProps) {
  // Demo mode is opt-in; default to false when not explicitly set
  const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true"

  const [downloads, setDownloads] = useState<UserDownload[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({})
  const [totalCount, setTotalCount] = useState(0)
  const [usingMockData, setUsingMockData] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchDownloads()
  }, [])

  const fetchDownloads = async () => {
    try {
      setLoading(true)
      setError(null)
      setRefreshing(true)

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"

      try {
        console.log("[v0] Attempting to fetch from localhost:8060...")
        const response = await fetch(`${API_BASE_URL}/downloads?limit=${limit}&include_dismissed=true`, {
          signal: AbortSignal.timeout(3000),
        })

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`)
        }

        const data = await response.json()
        const downloadsData = (data.downloads || []).map((download: any) => ({
          job_id: download.job_id,
          original_filename: download.original_filename,
          converted_filename: download.converted_filename,
          device_profile: download.device_profile,
          input_file_size: download.input_file_size,
          output_file_size: download.output_file_size,
          completed_at: download.completed_at,
          actual_duration: download.actual_duration,
          download_url: `${API_BASE_URL}${download.download_url}`,
          status: download.status || "COMPLETE",
          progress: download.progress || 100,
        }))

        console.log("[v0] Successfully fetched from localhost:8060", { count: downloadsData.length })
        setDownloads(downloadsData)
        setTotalCount(data.total || downloadsData.length)
        setUsingMockData(false)
      } catch (apiError) {
        if (demoMode) {
          console.log("[v0] API not reachable, using mock data (demo mode)", {
            error: apiError instanceof Error ? apiError.message : String(apiError),
          })
          await new Promise((resolve) => setTimeout(resolve, 300))
          setDownloads(mockData.myDownloads as UserDownload[])
          setTotalCount(mockData.myDownloads.length)
          setUsingMockData(true)
        } else {
          throw apiError
        }
      }
    } catch (error) {
      console.error("[MyDownloads] Error fetching downloads:", error)
      setError(error instanceof Error ? error.message : "Failed to load downloads")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleDownload = async (download: UserDownload) => {
    try {
      setDownloadingFiles((prev) => ({ ...prev, [download.job_id]: true }))

      if (usingMockData) {
        await new Promise((resolve) => setTimeout(resolve, 1500))
        toast.success(`Mock download: ${download.converted_filename}`)
        setDownloadingFiles((prev) => ({ ...prev, [download.job_id]: false }))
        return
      }

      const response = await fetch(download.download_url!)
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = download.converted_filename || `converted_${download.original_filename}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success(`Downloaded: ${download.converted_filename}`)
    } catch (error) {
      console.error("[MyDownloads] Download error:", error)
      toast.error("Failed to download file", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    } finally {
      setDownloadingFiles((prev) => ({ ...prev, [download.job_id]: false }))
    }
  }

  const handleDeleteById = async (id: string) => {
    const d = downloads.find((x) => x.job_id === id)
    if (!d) {
      toast.error("Failed to delete download", { description: "Item not found in list" })
      return
    }
    await handleDelete(d)
  }

  const handleDelete = async (download: UserDownload) => {
    if (usingMockData && demoMode) {
      toast.info(`Delete clicked for ${download.converted_filename}`)
      return
    }

    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"
      const res = await fetch(`${API_BASE_URL}/downloads/${download.job_id}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error || `Delete failed (${res.status})`)
      }
      setDownloads((prev) => prev.filter((d) => d.job_id !== download.job_id))
      setTotalCount((c) => Math.max(0, c - 1))
      toast.success(`Deleted ${download.converted_filename}`)
    } catch (e) {
      toast.error("Failed to delete download", { description: e instanceof Error ? e.message : String(e) })
    }
  }

  

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Unknown"
    try {
      const date = new Date(dateString)
      return date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    } catch {
      return "Unknown"
    }
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

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Conversions</CardTitle>
          <CardDescription>Loading your converted files...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-2 flex-1">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
              <Skeleton className="h-9 w-24" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Conversions</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button onClick={fetchDownloads} className="mt-4 bg-transparent" variant="outline">
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
          <CardDescription>No completed conversions yet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>Convert some files to see them here!</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>My Downloads</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={fetchDownloads}
            disabled={refreshing}
            aria-label="Refresh downloads list"
            className="h-8 w-8 shrink-0"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
        <CardDescription>
          {totalCount} completed conversion{totalCount !== 1 ? "s" : ""}
          {usingMockData && demoMode && (
            <Badge variant="outline" className="ml-2 text-xs">
              Demo Mode
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {downloads.map((download) => {
              const fileData = {
                id: download.job_id,
                jobId: download.job_id,
                name: download.converted_filename || download.original_filename,
                size: download.output_file_size || download.input_file_size,
                status: download.status,
                upload_progress: download.status === "UPLOADING" ? { percentage: download.progress } : undefined,
                // No processing_progress in downloads view; progress is driven by ETA in queue only
                error: download.status === "ERROR" ? "Conversion failed" : undefined,
                isConverted: download.status === "COMPLETE",
              }

              return (
                <motion.div
                  key={download.job_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                >
                  <FileConversionCard
                    file={fileData}
                    onDownload={() => handleDownload(download)}
                    onDelete={(id: string) => handleDeleteById(id)}
                    showActions={true}
                    isDownloading={downloadingFiles[download.job_id]}
                    context="downloads"
                  />
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}
