"use client"
import { User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import Link from "next/link"
import { useState, useEffect } from "react"
import { removeSessionKey } from "@/lib/session"
import { SignInButton, SignOutButton, useUser } from "@clerk/nextjs"

export function Navbar() {
  const { isLoaded, isSignedIn, user } = useUser()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleLogout = () => {
    removeSessionKey()
    console.log("Session key cleared from localStorage on logout")
  }

  if (!mounted || !isLoaded) {
    return (
      <nav className="flex items-center gap-4">
        <div className="w-24 h-9" />
      </nav>
    )
  }

  return (
    <nav className="flex items-center gap-4">
      <div className="flex items-center gap-2">
        {isSignedIn ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full hover:text-theme-medium">
                <User className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem asChild>
                <Link href="/account" className="cursor-pointer">
                  My Account
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem>
                <SignOutButton>
                  <button className="w-full text-left" onClick={handleLogout}>
                    Logout
                  </button>
                </SignOutButton>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <SignInButton mode="modal">
            <Button variant="ghost" size="sm" className="hover:bg-theme-medium/10 hover:text-theme-medium">
              Login
            </Button>
          </SignInButton>
        )}
      </div>
    </nav>
  )
}
