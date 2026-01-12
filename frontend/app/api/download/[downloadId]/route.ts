import { type NextRequest, NextResponse } from "next/server";
import { log, logError, logDebug } from "@/lib/logger";

// Configure the route to handle large files
export const config = {
  api: {
    responseLimit: false,
  },
};


export async function GET(
  request: Request,
  context: { params: Promise<{ downloadId: string }> },
) {
  const { downloadId } = await context.params;
  try {
    log(`API route: Received download request for ID: ${downloadId}`);
    // Determine API base URL
    const apiBaseUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060";
    // Require session key from client request header
    const sessionKey = request.headers.get("X-Session-Key");
    if (!sessionKey) {
      return NextResponse.json(
        { success: false, error: "No session key provided" },
        { status: 401 }
      );
    }
    log(`API route: Using session key from header: ${sessionKey}`);
    const downloadUrl = `${apiBaseUrl}/download/${downloadId}`;
    log(`API route: Using API base URL: ${apiBaseUrl}`);
    log(`API route: Forwarding download request to: ${downloadUrl}`);

    try {
      log(`API route: Sending request to ${downloadUrl}`);
      const response = await fetch(downloadUrl, {
        method: "GET",
        headers: {
          Accept: "*/*",
          "X-Session-Key": sessionKey,
        },
        redirect: "manual",
      });

      log("API route: Download response status:", response.status);
      logDebug(
        "API route: Download response headers", downloadId, {
          headers: Object.fromEntries(response.headers.entries())
        }
      );

      // If we got a redirect (to a presigned URL), return it as JSON
      if (response.status >= 300 && response.status < 400) {
        const location = response.headers.get("location");
        log(`API route: Received redirect to ${location}`);
        return NextResponse.json(
          { signedUrl: location },
          { status: 200 }
        );
      }

      // If the response is not OK, try to parse the error
      if (!response.ok) {
        logError("API route: Download response not OK");

        // Try to get the error as text
        const errorText = await response.text();
        logError("API route: Download error text:", errorText);

        // Try to parse as JSON if possible
        try {
          if (errorText && errorText.trim().startsWith("{")) {
            const errorData = JSON.parse(errorText);
            return NextResponse.json(
              { error: errorData.error || errorData.message || "API error" },
              { status: response.status },
            );
          } else {
            // If not JSON, return the text as the error
            return NextResponse.json(
              { error: errorText || "API error" },
              { status: response.status },
            );
          }
        } catch (parseError) {
          logError("API route: Error parsing error response:", parseError);
          return NextResponse.json(
            { error: errorText || "API error" },
            { status: response.status },
          );
        }
      }

      // Get the content type and other headers
      const contentType =
        response.headers.get("content-type") || "application/octet-stream";
      const contentDisposition =
        response.headers.get("content-disposition") || "";

      // Extract filename from content-disposition
      const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
      const filename = filenameMatch
        ? filenameMatch[1]
        : `download-${downloadId}`;

      // Ensure the content-disposition is set to attachment with the extracted filename
      const finalContentDisposition = `attachment; filename="${filename}"`;

      // Return the signed URL instead of streaming the file
      const signedUrl = response.url; // Assuming the response URL is the signed URL
      return NextResponse.json({ signedUrl }, { status: 200 });
    } catch (fetchError) {
      logError("API route: Download fetch error:", fetchError);

      // Try to provide more detailed error information
      const errorDetails = {
        message:
          fetchError instanceof Error ? fetchError.message : String(fetchError),
        name: fetchError instanceof Error ? fetchError.name : "Unknown",
        stack: fetchError instanceof Error ? fetchError.stack : undefined,
      };
      logError("Error details:", errorDetails);

      // Check if it's a network error
      if (
        fetchError instanceof TypeError &&
        fetchError.message.includes("fetch")
      ) {
        return NextResponse.json(
          {
            status: "error",
            message:
              "Network error: Could not connect to the download API. Please check your network connection or try again later.",
            error: errorDetails.message,
          },
          { status: 503 }, // Service Unavailable
        );
      }

      return NextResponse.json(
        {
          error: errorDetails.message,
          details: errorDetails,
        },
        { status: 500 },
      );
    }
  } catch (error) {
    logError("API download route error:", error);

    const errorDetails = {
      message: error instanceof Error ? error.message : String(error),
      name: error instanceof Error ? error.name : "Unknown",
      stack: error instanceof Error ? error.stack : undefined,
    };

    return NextResponse.json(
      {
        error: errorDetails.message,
        details: errorDetails,
      },
      { status: 500 },
    );
  }
}
