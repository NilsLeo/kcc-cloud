import { NextResponse } from "next/server"
import { log, logError } from "@/lib/logger"

export async function GET() {
  try {
    // Use the specific API URL from environment variables
    const apiUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060"
    log("Testing connection to API:", apiUrl)

    // Try to connect to the API
    try {
      const response = await fetch(`${apiUrl}/`, {
        method: "HEAD",
        // Short timeout to avoid long waits
        signal: AbortSignal.timeout(5000),
      })

      log("Connection test response status:", response.status)

      return NextResponse.json({
        success: true,
        message: `API is reachable at ${apiUrl}`,
        status: response.status,
        fullApiUrl: apiUrl,
      })
    } catch (error) {
      logError("API connection test error:", error)

      return NextResponse.json(
        {
          error: "Could not connect to API server",
          details: error instanceof Error ? error.message : String(error),
          apiUrl: apiUrl,
        },
        { status: 500 },
      )
    }
  } catch (error) {
    logError("Test connection route error:", error)

    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Internal server error" },
      { status: 500 },
    )
  }
}
