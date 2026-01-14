"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, Clock, FileText, Trash2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"

export type ConversionHistoryItem = {
  id: string
  originalName: string
  convertedName: string
  timestamp: number
  device: string
  size: number
}

interface RecentConversionsProps {
  history: ConversionHistoryItem[]
  onReconvert?: (originalName: string) => void
}

export function RecentConversions({ history, onReconvert }: RecentConversionsProps) {
  const clearHistory = () => {
    localStorage.removeItem("conversionHistory")
    toast.success("Conversion history cleared")
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  if (history.length === 0) return null

  return (
    <Card className="mb-8">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Recent Conversions</CardTitle>
          </div>
          <Button variant="ghost" size="sm" onClick={clearHistory} aria-label="Clear history">
            <Trash2 className="h-4 w-4 mr-1" />
            Clear
          </Button>
        </div>
        <CardDescription>Your recently converted manga files</CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-2">
          <AnimatePresence>
            {history.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center justify-between p-3 rounded-md bg-muted/50 hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium text-sm">{item.convertedName}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{formatDate(item.timestamp)}</span>
                      <span>•</span>
                      <span>{item.device}</span>
                      <span>•</span>
                      <span>{formatFileSize(item.size)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {onReconvert && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onReconvert(item.originalName)}
                      aria-label={`Reconvert ${item.originalName}`}
                    >
                      Reconvert
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label={`Download ${item.convertedName}`}
                    onClick={() => {
                      toast.info("This would download the file in a real app")
                    }}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  )
}
