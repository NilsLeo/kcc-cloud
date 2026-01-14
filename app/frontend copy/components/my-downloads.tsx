"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, FileText, Loader2, Clock, HardDrive, AlertCircle } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatFileSize } from "@/lib/utils"

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
}

interface MyDownloadsProps {
  limit?: number
}

export function MyDownloads({ limit = 100 }: MyDownloadsProps) {
  const [downloads, setDownloads] = useState<UserDownload[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({})
  const [totalCount, setTotalCount] = useState(0)

  useEffect(() => {
    fetchDownloads()
  }, [])

  const fetchDownloads = async () => {
    try {
      setLoading(true)
      setError(null)

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"
      const response = await fetch(`${API_BASE_URL}/downloads?limit=${limit}&include_dismissed=true`)

      if (!response.ok) {
        throw new Error(`Failed to fetch downloads: ${response.status}`)
      }

      const data = await response.json()

      // Map downloads to component format
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
      }))

      setDownloads(downloadsData)
      setTotalCount(data.total || downloadsData.length)
    } catch (error) {
      console.error("[MyDownloads] Error fetching downloads:", error)
      setError(error instanceof Error ? error.message : "Failed to load downloads")
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (download: UserDownload) => {
    try {
      setDownloadingFiles(prev => ({ ...prev, [download.job_id]: true }))

      // Download the file
      const response = await fetch(download.download_url)

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
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
        description: error instanceof Error ? error.message : "Unknown error"
      })
    } finally {
      setDownloadingFiles(prev => ({ ...prev, [download.job_id]: false }))
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Unknown"
    try {
      const date = new Date(dateString)
      return date.toLocaleString()
    } catch {
      return "Unknown"
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "Unknown"
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    }
    return `${seconds}s`
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
          <Button onClick={fetchDownloads} className="mt-4" variant="outline">
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
          <CardTitle>Recent Conversions</CardTitle>
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
        <CardTitle>Recent Conversions</CardTitle>
        <CardDescription>
          {totalCount} completed conversion{totalCount !== 1 ? 's' : ''}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {downloads.map((download) => (
              <motion.div
                key={download.job_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -100 }}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
              >
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <p className="font-medium truncate">{download.converted_filename}</p>
                    <Badge variant="secondary" className="flex-shrink-0">
                      {download.device_profile}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <HardDrive className="h-3 w-3" />
                      {formatFileSize(download.output_file_size || 0)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(download.completed_at)}
                    </span>
                    {download.actual_duration && (
                      <span>Duration: {formatDuration(download.actual_duration)}</span>
                    )}
                  </div>
                </div>
                <Button
                  onClick={() => handleDownload(download)}
                  disabled={downloadingFiles[download.job_id]}
                  size="sm"
                  className="flex-shrink-0"
                >
                  {downloadingFiles[download.job_id] ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Downloading
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Download
                    </>
                  )}
                </Button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        {downloads.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <Button onClick={fetchDownloads} variant="outline" className="w-full">
              Refresh List
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
