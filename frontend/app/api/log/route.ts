import { NextRequest, NextResponse } from 'next/server';
import { logger } from "@/lib/logger";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // DISABLED log forwarding to eliminate errors during debugging
    // Just log locally and return success
    console.log('Frontend log (not forwarded):', body);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error handling log request:', error);
    return NextResponse.json(
      { error: 'Failed to log message' },
      { status: 500 }
    );
  }
}
