"use client"

import type React from "react"
import { ClerkProvider } from "@clerk/nextjs"

const isClerkConfigured = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

export function ConditionalClerkProvider({ children }: { children: React.ReactNode }) {
  if (!isClerkConfigured) {
    return <>{children}</>
  }

  return <ClerkProvider>{children}</ClerkProvider>
}
