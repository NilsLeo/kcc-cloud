import { type NextRequest, NextResponse } from "next/server"
import { logError } from "@/lib/logger"

export async function GET(request: NextRequest, context: { params: { jobId: string } }) {
  try {
    // Properly await params before accessing properties
    const { jobId } = await context.params

    // Use API_BASE_URL for server-side requests (Docker network), fallback to NEXT_PUBLIC_API_URL
    const apiBaseUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL

    if (!apiBaseUrl) {
      console.error("API_BASE_URL or NEXT_PUBLIC_API_URL environment variable is not set")
      return NextResponse.json({ error: "Backend API URL not configured" }, { status: 500 })
    }
    // Require session key from client request header
    const sessionKey = request.headers.get("X-Session-Key")
    if (!sessionKey) {
      return NextResponse.json({ success: false, error: "No session key provided" }, { status: 401 })
    }
    // Call the backend API to check job status
    const statusUrl = `${apiBaseUrl}/status/${jobId}`

    const response = await fetch(statusUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-Session-Key": sessionKey,
      },
    })

    // Get the response as text first
    const responseText = await response.text()

    // Try to parse the JSON response
    try {
      const jsonData = JSON.parse(responseText)

      // If the job is completed, transform the response to match our expected format
      if (jsonData.status === "COMPLETE") {
        return NextResponse.json({
          status: "COMPLETE",
          download_id: jobId,
          filename: jsonData.filename || (jsonData.output_file ? jsonData.output_file.split("/").pop() : null),
          input_filename: jsonData.input_filename,
          input_file_size: jsonData.input_file_size,
          output_file_size: jsonData.output_file_size,
          device_profile: jsonData.device_profile,
        })
      } else if (
        response.status === 400 ||
        jsonData.error ||
        jsonData.status === "ERRORED" ||
        jsonData.status === "CANCELLED"
      ) {
        // Job failed or cancelled
        let errorMessage = "Conversion failed"

        if (jsonData.status === "CANCELLED") {
          errorMessage = "Job was cancelled due to timeout"
        } else if (jsonData.error) {
          // Use the actual error message from backend
          errorMessage = jsonData.error
        } else if (jsonData.detail) {
          errorMessage = jsonData.detail
        } else if (jsonData.message) {
          errorMessage = jsonData.message
        }

        return NextResponse.json({
          status: jsonData.status || "ERRORED",
          error: errorMessage,
        })
      } else if (
        response.status === 202 ||
        jsonData.status === "QUEUED" ||
        jsonData.status === "UPLOADING" ||
        jsonData.status === "PROCESSING"
      ) {
        // Job is still processing
        const pendingResponse = {
          status: jsonData.status || "QUEUED", // Preserve actual status instead of hardcoding "QUEUED"
          message: jsonData.message || "Your file is still being processed",
        }

        // Pass through progress information
        if (jsonData.progress_percent !== undefined) {
          pendingResponse.progress_percent = jsonData.progress_percent
        }
        if (jsonData.upload_progress !== undefined) {
          pendingResponse.upload_progress = jsonData.upload_progress
        }
        if (jsonData.projected_eta !== undefined) {
          pendingResponse.projected_eta = jsonData.projected_eta
        }
        if (jsonData.remaining_seconds !== undefined) {
          pendingResponse.remaining_seconds = jsonData.remaining_seconds
        }

        return NextResponse.json(pendingResponse)
      }

      // Pass through the response as-is for other cases
      return NextResponse.json(jsonData, { status: response.status })
    } catch (parseError) {
      logError("API route: Error parsing status response:", parseError, "Response text:", responseText)
      return NextResponse.json({ error: "Invalid JSON response from status API" }, { status: 500 })
    }
  } catch (error) {
    logError("Error checking job status:", error)

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Internal server error",
      },
      { status: 500 },
    )
  }
}
