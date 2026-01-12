import { type NextRequest, NextResponse } from "next/server";
import { log, logError, logDebug } from "@/lib/logger";

export async function GET(request: NextRequest) {
  try {
    log("API route: Received session registration request");

    // Log all environment variables for debugging
    logDebug("Environment variables", {
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      NODE_ENV: process.env.NODE_ENV,
    });

    // Use a default API URL if not set in environment variables
    const apiUrl = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8060";
    log(`API route: Using API URL: ${apiUrl}`);

    // Call the backend API to register a new session
    const registerUrl = `${apiUrl}/register`;
    log(`API route: Registering at: ${registerUrl}`);

    const response = await fetch(registerUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    log(`API route: Registration response status: ${response.status}`);

    // Get the response as text first
    const responseText = await response.text();

    // Try to parse the JSON response
    try {
      const jsonData = JSON.parse(responseText);
      log("API route: Registration successful", jsonData);
      return NextResponse.json(jsonData);
    } catch (parseError) {
      logError(
        "API route: Error parsing registration response", {
          parseError: parseError.message,
          responseText,
          error: parseError
        }
      );
      return NextResponse.json(
        { error: "Invalid JSON response from registration API" },
        { status: 500 },
      );
    }
  } catch (error) {
    logError("Error during session registration:", error);

    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Internal server error",
      },
      { status: 500 },
    );
  }
}
