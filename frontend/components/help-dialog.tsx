"use client"

import type React from "react"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { HelpCircle, FileUp, Smartphone, Settings, Play, Info, Keyboard } from "lucide-react"

interface HelpDialogProps {
  children?: React.ReactNode
}

export function HelpDialog({ children }: HelpDialogProps) {
  const [open, setOpen] = useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children || (
          <Button variant="ghost" size="icon" aria-label="Help">
            <HelpCircle className="h-5 w-5" />
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>MangaConverter.com Help</DialogTitle>
          <DialogDescription>
            Learn how to use MangaConverter.com to convert your manga files for e-readers
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="getting-started" className="mt-4">
          <TabsList className="grid grid-cols-4">
            <TabsTrigger value="getting-started">Getting Started</TabsTrigger>
            <TabsTrigger value="features">Features</TabsTrigger>
            <TabsTrigger value="faq">FAQ</TabsTrigger>
            <TabsTrigger value="shortcuts">Shortcuts</TabsTrigger>
          </TabsList>

          <TabsContent value="getting-started" className="space-y-4 mt-4">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <FileUp className="h-5 w-5 text-primary" />
                Step 1: Upload Files
              </h3>
              <p className="text-muted-foreground">
                Start by uploading your manga files. You can drag and drop files onto the upload area or click the
                "Choose files" button to select files from your device.
              </p>
              <div className="bg-muted p-3 rounded-md text-sm">
                <p className="font-medium">Supported formats:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>.cbz - Comic Book ZIP</li>
                  <li>.zip - ZIP archive containing images</li>
                  <li>.cbr - Comic Book RAR</li>
                  <li>.rar - RAR archive containing images</li>
                  <li>.cb7 - Comic Book 7Z</li>
                  <li>.7z - 7Z archive containing images</li>
                  <li>.pdf - PDF document</li>
                  <li>.epub - EPUB ebook</li>
                </ul>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Smartphone className="h-5 w-5 text-primary" />
                Step 2: Select Device
              </h3>
              <p className="text-muted-foreground">
                Choose your e-reader device from the dropdown menu. This will optimize the conversion settings for your
                specific device's screen size and capabilities.
              </p>
              <div className="bg-muted p-3 rounded-md text-sm">
                <p className="font-medium">Supported devices include:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Kindle (various models)</li>
                  <li>Kobo (various models)</li>
                  <li>reMarkable</li>
                  <li>Other e-readers</li>
                </ul>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Settings className="h-5 w-5 text-primary" />
                Step 3: Configure Options (Optional)
              </h3>
              <p className="text-muted-foreground">
                Adjust advanced settings if needed. The default settings are optimized for most manga, but you can
                customize them for your specific needs.
              </p>
              <div className="bg-muted p-3 rounded-md text-sm">
                <p className="font-medium">Key options include:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>Manga Style - Right-to-left reading and splitting</li>
                  <li>High Quality - Improve image quality</li>
                  <li>Output Format - Choose between EPUB, MOBI, CBZ, etc.</li>
                  <li>And many more advanced settings</li>
                </ul>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Play className="h-5 w-5 text-primary" />
                Step 4: Start Conversion
              </h3>
              <p className="text-muted-foreground">
                Click the "Start Conversion" button to begin processing your files. Files will be converted one by one,
                and the converted files will be automatically downloaded when ready.
              </p>
              <div className="bg-muted p-3 rounded-md text-sm">
                <p className="font-medium">During conversion:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li>You can see the progress of the current conversion</li>
                  <li>Files are processed in the order they appear in the queue</li>
                  <li>You can reorder files by dragging them before starting conversion</li>
                </ul>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="features" className="space-y-4 mt-4">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Key Features</h3>
              <ul className="space-y-3">
                <li className="flex gap-2">
                  <div className="bg-primary/10 p-2 rounded-md">
                    <FileUp className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Batch Processing</p>
                    <p className="text-sm text-muted-foreground">Convert multiple files in a single session</p>
                  </div>
                </li>
                <li className="flex gap-2">
                  <div className="bg-primary/10 p-2 rounded-md">
                    <Smartphone className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Device-Specific Optimization</p>
                    <p className="text-sm text-muted-foreground">Tailored output for your specific e-reader model</p>
                  </div>
                </li>
                <li className="flex gap-2">
                  <div className="bg-primary/10 p-2 rounded-md">
                    <Settings className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Advanced Customization</p>
                    <p className="text-sm text-muted-foreground">Fine-tune conversion settings for perfect results</p>
                  </div>
                </li>
                <li className="flex gap-2">
                  <div className="bg-primary/10 p-2 rounded-md">
                    <Info className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Conversion History</p>
                    <p className="text-sm text-muted-foreground">Keep track of your recently converted files</p>
                  </div>
                </li>
                <li className="flex gap-2">
                  <div className="bg-primary/10 p-2 rounded-md">
                    <Keyboard className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Keyboard Shortcuts</p>
                    <p className="text-sm text-muted-foreground">Navigate and control the app efficiently</p>
                  </div>
                </li>
              </ul>
            </div>
          </TabsContent>

          <TabsContent value="faq" className="space-y-4 mt-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold">Frequently Asked Questions</h3>

                <div className="space-y-1">
                  <h4 className="font-medium">What file formats can I convert?</h4>
                  <p className="text-sm text-muted-foreground">
                    You can convert CBZ, ZIP, CBR, RAR, and PDF files. These formats should contain manga or comic
                    images.
                  </p>
                </div>

                <div className="space-y-1 mt-3">
                  <h4 className="font-medium">Which e-readers are supported?</h4>
                  <p className="text-sm text-muted-foreground">
                    We support a wide range of e-readers including various Kindle models, Kobo devices, reMarkable
                    tablets, and more. Select your specific device from the dropdown menu for optimal results.
                  </p>
                </div>

                <div className="space-y-1 mt-3">
                  <h4 className="font-medium">What is "Manga Style"?</h4>
                  <p className="text-sm text-muted-foreground">
                    Manga Style enables right-to-left reading order and appropriate page splitting for Japanese manga.
                    Enable this option for manga that reads from right to left.
                  </p>
                </div>

                <div className="space-y-1 mt-3">
                  <h4 className="font-medium">How do I reorder files in the queue?</h4>
                  <p className="text-sm text-muted-foreground">
                    Before starting conversion, you can drag and drop files in the queue to reorder them. Simply click
                    and hold on the grip icon next to a file and drag it to the desired position.
                  </p>
                </div>

                <div className="space-y-1 mt-3">
                  <h4 className="font-medium">Where are my converted files saved?</h4>
                  <p className="text-sm text-muted-foreground">
                    Converted files are automatically downloaded to your default download location. You can also find
                    your recent conversions in the "Recent Conversions" section at the top of the page.
                  </p>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="shortcuts" className="space-y-4 mt-4">
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Keyboard Shortcuts</h3>
              <p className="text-muted-foreground">
                Use these keyboard shortcuts to navigate the app more efficiently.
              </p>

              <div className="grid gap-4 py-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Show keyboard shortcuts</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    Shift + ?
                  </kbd>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Go to Upload tab</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    u
                  </kbd>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Go to Device & Options tab</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    d
                  </kbd>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Go to Queue & Convert tab</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    q
                  </kbd>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Start conversion (when in Queue tab)</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    c
                  </kbd>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Close dialogs</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    Esc
                  </kbd>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Toggle advanced options</span>
                  <kbd className="px-2 py-1.5 text-xs font-semibold text-muted-foreground bg-muted rounded border">
                    Space
                  </kbd>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
