import { type NextRequest, NextResponse } from "next/server"
import { log, logError } from "@/lib/logger"

export async function POST(request: NextRequest, context: { params: { jobId: string } }) {
  try {
    const { jobId } = await context.params
    const sessionKey = request.headers.get("X-Session-Key")

    if (!sessionKey) {
      return NextResponse.json({ error: "No session key provided" }, { status: 401 })
    }

    const apiBaseUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL

    if (!apiBaseUrl) {
      console.error("API_BASE_URL or NEXT_PUBLIC_API_URL environment variable is not set")
      return NextResponse.json({ error: "Backend API URL not configured" }, { status: 500 })
    }

    log("Cancelling job", jobId, {
      backend_url: `${apiBaseUrl}/jobs/${jobId}/cancel`,
    })

    const res = await fetch(`${apiBaseUrl}/jobs/${jobId}/cancel`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Key": sessionKey,
      },
    })

    if (!res.ok) {
      const errorText = await res.text()
      let errorData
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { error: errorText }
      }

      logError("Backend job cancellation failed", jobId, {
        status: res.status,
        error: errorData.error || errorText,
      })

      return NextResponse.json(
        { error: errorData.error || "Failed to cancel job" },
        { status: res.status }
      )
    }

    const data = await res.json()

    log("Job cancelled successfully", jobId, {
      new_status: data.status,
    })

    return NextResponse.json(data)
  } catch (error) {
    logError("Frontend API: Exception in job cancellation", {
      error: error instanceof Error ? error.message : String(error),
    })

    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 }
    )
  }
}
