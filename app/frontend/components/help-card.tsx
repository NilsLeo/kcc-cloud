"use client"

import { HelpCircle, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function HelpCard() {
  const handleEmailClick = () => {
    window.location.href =
      "mailto:support@mangaconverter.com?subject=Support Request - MangaConverter&body=Hi, I need help with:%0D%0A%0D%0A"
  }

  return (
    <Card className="border-2 border bg-muted/50 dark:bg-muted/20">
      <CardHeader>
        <div className="flex items-center gap-2">
          <HelpCircle className="h-5 w-5 text-foreground" />
          <CardTitle>Need Help?</CardTitle>
        </div>
        <CardDescription>
          Have questions or need assistance? We're here to help! Reach out to our support team and we'll get back to you
          as soon as possible.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          onClick={handleEmailClick}
          className="w-full gap-2 text-base font-semibold bg-orange-600 hover:bg-orange-700"
          size="lg"
        >
          <Mail className="h-5 w-5" />
          Contact Support
        </Button>
        <p className="text-xs text-muted-foreground text-center mt-3">Email: support@mangaconverter.com</p>
      </CardContent>
    </Card>
  )
}
