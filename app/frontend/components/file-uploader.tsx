"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Upload, FileUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { validateFileExtension, UnsupportedFileFormatError } from "@/lib/fileValidation"

interface FileUploaderProps {
  onFilesSelected: (files: File[]) => void
  disabled?: boolean
  acceptedTypes: string[]
  maxFiles: number
  maxFileSize?: number
  compact?: boolean
  contentType?: "comic" | "manga"
}

export function FileUploader({
  onFilesSelected,
  disabled = false,
  acceptedTypes,
  maxFiles,
  maxFileSize = 1024 * 1024 * 1024,
  compact = false,
  contentType = "comic",
}: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isHoveringIcon, setIsHoveringIcon] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    if (disabled) return

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files)

      const validExtensionFiles = files.filter((file) => {
        try {
          validateFileExtension(file.name)
          return true
        } catch (error) {
          if (error instanceof UnsupportedFileFormatError) {
            toast.error("Invalid file", {
              description: error.message,
            })
            return false
          }
          throw error
        }
      })

      if (validExtensionFiles.length === 0) {
        return
      }

      const validSizeFiles = validExtensionFiles.filter((file) => {
        if (file.size > maxFileSize) {
          toast.error(`File too large: ${file.name}`, {
            description: `Maximum file size is ${formatFileSize(maxFileSize)}`,
          })
          return false
        }
        return true
      })

      if (validSizeFiles.length > 0) {
        onFilesSelected(validSizeFiles)
        toast.success(`${validSizeFiles.length} file${validSizeFiles.length !== 1 ? "s" : ""} added`)
      }
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files)

      // Validate file extensions first
      const validExtensionFiles = files.filter((file) => {
        try {
          validateFileExtension(file.name)
          return true
        } catch (error) {
          if (error instanceof UnsupportedFileFormatError) {
            toast.error("Invalid file", {
              description: error.message,
            })
            return false
          }
          throw error
        }
      })

      if (validExtensionFiles.length === 0) {
        return
      }

      // Then validate file sizes
      const validSizeFiles = validExtensionFiles.filter((file) => {
        if (file.size > maxFileSize) {
          toast.error(`File too large: ${file.name}`, {
            description: `Maximum file size is ${formatFileSize(maxFileSize)}`,
          })
          return false
        }
        return true
      })

      if (validSizeFiles.length > 0) {
        onFilesSelected(validSizeFiles)
        toast.success(`${validSizeFiles.length} file${validSizeFiles.length !== 1 ? "s" : ""} added`)
      }
    }
  }

  const handleButtonClick = () => {
    if (disabled) {
      return
    }
    fileInputRef.current?.click()
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const BatmanIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="1.95 2 230.12 256" className="h-12 w-12 fill-theme-medium">
      <path d="M232.043,157.557L216.22,2l-32.915,51.122c0,0-28.733-21.024-66.301-21.024c-37.577,0-60.744,17.332-60.744,17.332L9.57,2  L1.957,157.557h4.675C11.901,213.818,59.385,258,117,258s105.099-44.182,110.368-100.443H232.043z M47.147,109.233  c2.105-7.719,11.19-11.065,17.794-6.556l35.635,24.35H42.293L47.147,109.233z M169.194,102.677  c6.604-4.508,15.698-1.163,17.803,6.556l4.845,17.794h-58.283L169.194,102.677z M117,238.185c-46.68,0-85.26-35.314-90.447-80.628  h180.893C202.26,202.871,163.68,238.185,117,238.185z M146.646,200.214H90.891v-16.932h55.755V200.214z" />
    </svg>
  )

  const KonohaIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" className="h-12 w-12 fill-theme-medium">
<path d="M38.892 14.296C26.973 19.323 15.061 32.693 15.01 41.102c-.009 1.359-2.437 8.367-13.59 39.218L.039 84.141l27.731-.321c31.091-.359 32.628-.667 41.006-8.237 18.829-17.01 3.415-50.678-20.822-45.48-20.01 4.292-21.144 34.431-1.379 36.658 12.603 1.421 18.192-11.422 8.707-20.006-1.841-1.666-2.037-1.62-4.623 1.079-2.699 2.817-2.699 2.82-.68 4.647 4.522 4.092 1.159 8.906-4.439 6.355-6.306-2.873-7.474-12.102-2.199-17.377 13.386-13.386 34.151 8.644 23.31 24.731-16.699 24.779-55.114-1.28-42.293-28.69 8.743-18.692 31.564-23.429 50.15-10.41l5.702 3.995 7.395-5.566c8.152-6.136 8.232-6.278 5.458-9.658-2.098-2.557-1.74-2.656-8.938 2.474l-3.978 2.835-8.663-4.293c-11.285-5.592-23.213-6.537-32.592-2.581M16 62.281c0 .371-1.105 3.609-2.455 7.196L11.09 76h15.259l-2.071-2.25c-1.138-1.237-3.467-4.476-5.174-7.196C17.397 63.834 16 61.911 16 62.281" fillRule="evenodd"/>

</svg>
  )

  if (compact) {
    return (
      <div
        className={cn(
          "border-2 border-dashed rounded-lg p-4 transition-all duration-200 relative overflow-hidden",
          isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50",
          disabled ? "opacity-50 cursor-not-allowed" : "",
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onMouseEnter={() => setIsHoveringIcon(true)}
        onMouseLeave={() => setIsHoveringIcon(false)}
      >
        <div className="absolute inset-0 bg-background/95 -z-10" />
        <div className="flex items-center justify-between gap-4 relative z-10">
          <div className="flex items-center gap-3">
            <div
              className="rounded-full bg-muted p-2 transition-all duration-300 cursor-pointer"
              onClick={handleButtonClick}
            >
              {isHoveringIcon || isDragging ? (
                contentType === "comic" ? (
                  <div className="h-4 w-4">
                    <BatmanIcon />
                  </div>
                ) : (
                  <div className="h-4 w-4">
                    <KonohaIcon />
                  </div>
                )
              ) : (
                <Upload className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
            <div>
              <p className="text-sm font-medium">Add more files</p>
              <p className="text-xs text-muted-foreground">Drag & drop or click to browse</p>
            </div>
          </div>
          <Button onClick={handleButtonClick} disabled={disabled} size="sm" variant="outline">
            <FileUp className="mr-2 h-3 w-3" />
            Browse
          </Button>
        </div>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          accept={acceptedTypes.join(",")}
          multiple
          className="hidden"
          disabled={disabled}
        />
      </div>
    )
  }

  return (
    <Card
      className={cn(
        "border-2 transition-all duration-200 relative overflow-hidden",
        isDragging ? "border-primary border-dashed scale-[1.01] shadow-md" : "border-input dark:border-input",
      )}
    >
      <CardContent className="p-6 relative z-10">
        <div
          className="flex flex-col items-center justify-center gap-4 py-8"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onMouseEnter={() => setIsHoveringIcon(true)}
          onMouseLeave={() => setIsHoveringIcon(false)}
        >
          <motion.div
            className="rounded-full bg-muted p-6 cursor-pointer"
            animate={{
              scale: isDragging ? 1.1 : 1,
            }}
            transition={{ type: "spring", stiffness: 300, damping: 15 }}
            onClick={handleButtonClick}
          >
            {isHoveringIcon || isDragging ? (
              contentType === "comic" ? (
                <BatmanIcon />
              ) : (
                <KonohaIcon />
              )
            ) : (
              <Upload className="h-12 w-12 text-muted-foreground" />
            )}
          </motion.div>
          <div className="text-center">
            <p className="text-lg font-medium">{isDragging ? "Drop files here" : "Drag and drop your files here"}</p>
            <p className="text-sm text-muted-foreground mt-1">Supported formats: {acceptedTypes.join(", ")}</p>
            <p className="text-sm text-muted-foreground mt-1">Maximum {maxFiles} files at once</p>
            <p className="text-sm text-muted-foreground mt-1">
              Maximum file size: <span className="font-medium text-primary">{formatFileSize(maxFileSize)}</span>
            </p>
          </div>
          <Button onClick={handleButtonClick} disabled={disabled} className="mt-2" size="lg">
            <FileUp className="mr-2 h-4 w-4" />
            Choose files
          </Button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileInputChange}
            accept={acceptedTypes.join(",")}
            multiple
            className="hidden"
            disabled={disabled}
          />
        </div>
      </CardContent>
    </Card>
  )
}
