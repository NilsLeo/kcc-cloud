"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { X, Sparkles, ChevronRight, ChevronLeft, FileUp, Smartphone, Settings, Play } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { useConverterMode } from "@/contexts/converter-mode-context"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function WelcomeGuide() {
  const { isComic } = useConverterMode()
  const [isVisible, setIsVisible] = useState(false)
  const [step, setStep] = useState(0)
  const [activeTab, setActiveTab] = useState("welcome")
  const contentType = isComic ? "comic" : "manga"

  useEffect(() => {
    // Check if this is the first visit
    const hasVisitedBefore = localStorage.getItem("hasVisitedBefore")
    if (!hasVisitedBefore) {
      setIsVisible(true)
    }
  }, [])

  const handleDismiss = () => {
    setIsVisible(false)
    localStorage.setItem("hasVisitedBefore", "true")
  }

  const steps = [
    {
      title: "Upload Files",
      description: `Drag and drop your ${contentType} files or click to browse`,
      icon: <FileUp className="h-10 w-10 text-primary" />,
      tip: "Supported formats: .cbz, .zip, .cbr, .rar, .pdf",
    },
    {
      title: "Select Device",
      description: "Choose your e-reader device for optimal conversion",
      icon: <Smartphone className="h-10 w-10 text-primary" />,
      tip: "The app will optimize the output based on your device's screen size and capabilities",
    },
    {
      title: "Configure Options",
      description: "Adjust advanced settings if needed",
      icon: <Settings className="h-10 w-10 text-primary" />,
      tip: "Most options have sensible defaults, but you can customize them for your specific needs",
    },
    {
      title: "Start Conversion",
      description: "Click the convert button to process your files",
      icon: <Play className="h-10 w-10 text-primary" />,
      tip: "Files will be processed one by one and automatically downloaded when ready",
    },
  ]

  if (!isVisible) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5 }}
      className="mb-8"
    >
      <Card className="overflow-hidden border-primary/20">
        <CardHeader className="pb-3 bg-primary/5">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary animate-pulse" />
              <CardTitle>Welcome to Comic & Manga Converter!</CardTitle>
            </div>
            <Button variant="ghost" size="sm" onClick={handleDismiss} aria-label="Dismiss welcome message">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <CardDescription>
            Your all-in-one solution for converting {contentType} files to e-reader formats
          </CardDescription>
        </CardHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <div className="px-6 pt-4">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="welcome">Welcome</TabsTrigger>
              <TabsTrigger value="guide">Quick Start Guide</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="welcome" className="mt-0">
            <CardContent className="pt-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-background p-4 rounded-lg shadow-sm">
                  <h3 className="font-medium mb-2">Easy to Use</h3>
                  <p className="text-sm text-muted-foreground">
                    Simple drag-and-drop interface for uploading and converting your {contentType} files
                  </p>
                </div>
                <div className="bg-background p-4 rounded-lg shadow-sm">
                  <h3 className="font-medium mb-2">Device Optimized</h3>
                  <p className="text-sm text-muted-foreground">
                    Tailored conversion settings for all popular e-readers
                  </p>
                </div>
                <div className="bg-background p-4 rounded-lg shadow-sm">
                  <h3 className="font-medium mb-2">Advanced Features</h3>
                  <p className="text-sm text-muted-foreground">
                    Fine-tune your conversions with powerful customization options
                  </p>
                </div>
              </div>
            </CardContent>

            <CardFooter className="flex justify-end pt-3 border-t border-primary/10">
              <Button onClick={() => setActiveTab("guide")}>
                See How It Works <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </CardFooter>
          </TabsContent>

          <TabsContent value="guide" className="mt-0">
            <CardContent className="pt-4">
              <AnimatePresence mode="wait">
                <motion.div
                  key={step}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="flex flex-col items-center text-center p-4"
                >
                  <div className="mb-4 p-3 rounded-full bg-primary/10">{steps[step].icon}</div>
                  <h3 className="text-xl font-semibold mb-2">{steps[step].title}</h3>
                  <p className="text-muted-foreground mb-4">{steps[step].description}</p>
                  <div className="bg-muted p-3 rounded-md text-sm italic">
                    <span className="font-medium">Tip:</span> {steps[step].tip}
                  </div>
                </motion.div>
              </AnimatePresence>
            </CardContent>

            <CardFooter className="flex justify-between pt-3 border-t">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStep((prev) => Math.max(0, prev - 1))}
                disabled={step === 0}
              >
                <ChevronLeft className="h-4 w-4 mr-1" /> Previous
              </Button>

              <div className="flex gap-1">
                {steps.map((_, i) => (
                  <div
                    key={i}
                    className={`h-1.5 w-6 rounded-full ${i === step ? "bg-primary" : "bg-muted"}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => setStep(i)}
                    aria-label={`Go to step ${i + 1}`}
                  />
                ))}
              </div>

              {step === steps.length - 1 ? (
                <Button size="sm" onClick={handleDismiss}>
                  Get Started
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setStep((prev) => Math.min(steps.length - 1, prev + 1))}
                >
                  Next <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              )}
            </CardFooter>
          </TabsContent>
        </Tabs>
      </Card>
    </motion.div>
  )
}
