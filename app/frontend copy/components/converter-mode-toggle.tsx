"use client"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { motion } from "framer-motion"
import { BookOpenText, BookText } from "lucide-react"
import { useConverterMode } from "@/contexts/converter-mode-context"

export function ConverterModeToggle() {
  const { mode, toggleMode } = useConverterMode()
  const isManga = mode === "manga"

  // Invert the checked state - now checked when in manga mode
  const isChecked = isManga

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="bg-background border rounded-full shadow-lg p-3 flex items-center gap-3">
        <div className="flex items-center gap-2">
          <motion.div
            animate={{
              scale: isManga ? 1 : 0.8,
              opacity: isManga ? 1 : 0.5,
            }}
          >
            <BookOpenText className="h-5 w-5 text-primary" />
          </motion.div>
          <Label htmlFor="converter-mode" className="cursor-pointer text-sm font-medium">
            {isManga ? "ComicConverter" : "MangaConverter"}
          </Label>
        </div>

        <Switch
          id="converter-mode"
          checked={isChecked}
          onCheckedChange={toggleMode}
          aria-label={`Switch to ${isManga ? "comic" : "manga"} converter`}
        />

        <motion.div
          animate={{
            scale: !isManga ? 1 : 0.8,
            opacity: !isManga ? 1 : 0.5,
          }}
        >
          <BookText className="h-5 w-5 text-primary" />
        </motion.div>
      </div>
    </div>
  )
}
