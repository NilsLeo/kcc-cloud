"use client"

import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, ArrowRight } from "lucide-react"
import Link from "next/link"

export function DownloadsPreviewCard() {
  return (
    <Card className="border-dashed">
      <CardHeader>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div className="hidden md:flex items-center gap-3">
            <div className="p-3 rounded-lg bg-primary/10 text-primary">
              <Download className="h-6 w-6" />
            </div>
            <CardTitle className="text-lg">My Downloads</CardTitle>
          </div>
          <Link href="/downloads" className="w-full md:w-auto">
            <Button variant="ghost" size="sm" className="w-full md:w-auto">
              Go to My Downloads
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </Link>
        </div>
      </CardHeader>
    </Card>
  )
}
