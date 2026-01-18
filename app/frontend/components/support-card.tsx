"use client"

import { MessageSquare } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function SupportCard() {
  const handleSupportClick = () => {
    window.open("https://github.com/yourusername/manga-converter/issues/new", "_blank", "noopener,noreferrer")
  }

  return (
    <Card className="border-2 bg-muted/30 dark:bg-muted/10">
      <CardHeader>
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          <CardTitle className="flex items-center gap-2">Need Help?</CardTitle>
        </div>
        <CardDescription>
          Have a question or found an issue? Report it on GitHub and we'll help you out.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          onClick={handleSupportClick}
          className="w-full gap-2 text-base font-semibold bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white"
          size="lg"
        >
          <MessageSquare className="h-5 w-5" />
          Report an Issue
        </Button>
      </CardContent>
    </Card>
  )
}
