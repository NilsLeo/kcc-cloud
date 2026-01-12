import { type NextRequest, NextResponse } from "next/server"
import { log, logError } from "@/lib/logger"

export async function PATCH(request: NextRequest, context: { params: { jobId: string } }) {
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

    console.log("[v0] Checking job status before calling start endpoint")
    const statusCheckRes = await fetch(`${apiBaseUrl}/status/${jobId}`, {
      method: "GET",
      headers: {
        "X-Session-Key": sessionKey,
      },
    })

    if (statusCheckRes.ok) {
      const statusData = await statusCheckRes.json()
      console.log("[v0] Current job status before start:", statusData.status)
      log("Job status before start endpoint", jobId, {
        current_status: statusData.status,
        about_to_call_start: true,
      })

      // If job is not in UPLOADING status, log detailed error
      if (statusData.status !== "UPLOADING") {
        logError("Job is not in UPLOADING status when start was called", jobId, {
          current_status: statusData.status,
          expected_status: "UPLOADING",
          error: "Status mismatch - job may have been cancelled or changed",
        })
      }
    } else {
      console.log("[v0] Failed to check status before start:", statusCheckRes.status)
    }

    log("Frontend API: Calling backend to start job", jobId, {
      backend_url: `${apiBaseUrl}/jobs/${jobId}/start`,
      has_session_key: !!sessionKey,
    })

    const res = await fetch(`${apiBaseUrl}/jobs/${jobId}/start`, {
      method: "PATCH",
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

      console.log("[v0] Backend start failed:", {
        status: res.status,
        error: errorData.error || errorText,
      })

      logError("Backend job start failed", jobId, {
        status: res.status,
        statusText: res.statusText,
        error: errorData.error || errorText,
        backend_response: errorData,
      })

      return NextResponse.json({ error: errorData.error || "Failed to start job processing" }, { status: res.status })
    }

    const data = await res.json()

    console.log("[v0] Backend start successful, new status:", data.status)

    log("Backend job start successful", jobId, {
      new_status: data.status,
    })

    return NextResponse.json(data)
  } catch (error) {
    console.log("[v0] Exception in job start:", error)

    logError("Frontend API: Exception in job start", {
      error: error instanceof Error ? error.message : String(error),
      error_type: error instanceof Error ? error.constructor.name : typeof error,
    })

    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 },
    )
  }
}
