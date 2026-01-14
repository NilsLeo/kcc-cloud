"use client"

import { useState, useEffect } from "react"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { HelpCircle, AlertTriangle, CheckCircle2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { AdvancedOptionsType } from "./manga-converter"
import { useConverterMode } from "@/contexts/converter-mode-context"

interface AdvancedOptionsProps {
  options: AdvancedOptionsType
  onChange: (options: Partial<AdvancedOptionsType>) => void
  deviceProfile: string
  contentType?: "comic" | "manga"
}

export function AdvancedOptions({ options, onChange, deviceProfile, contentType = "manga" }: AdvancedOptionsProps) {
  const { mode, setMode } = useConverterMode()
  const isMangaMode = mode === "manga"

  const isOtherProfile = deviceProfile === "OTHER"
  const isComic = contentType === "comic"

  const hasCustomWidth = options.customWidth && options.customWidth > 0
  const hasCustomHeight = options.customHeight && options.customHeight > 0
  const hasValidOutputFormat = options.outputFormat && options.outputFormat !== "Auto"
  const allRequiredFieldsFilled = hasCustomWidth && hasCustomHeight && hasValidOutputFormat
  const hasRequiredFields = isOtherProfile && !allRequiredFieldsFilled

  const [expanded, setExpanded] = useState<string | undefined>(undefined)

  // Update expanded state when device profile changes
  useEffect(() => {
    if (isOtherProfile && expanded !== "advanced-options") {
      setExpanded("advanced-options")
    }
  }, [isOtherProfile, expanded])

  const handleCheckboxChange = (field: keyof AdvancedOptionsType) => {
    onChange({ [field]: !options[field] })
  }

  const handleNumberChange = (field: keyof AdvancedOptionsType, value: string) => {
    const numValue = Number.parseFloat(value)
    if (!isNaN(numValue)) {
      onChange({ [field]: numValue })
    }
  }

  const handleSelectChange = (field: keyof AdvancedOptionsType, value: string) => {
    onChange({ [field]: field === "splitter" ? Number.parseInt(value) : value })
  }

  const handleTextChange = (field: keyof AdvancedOptionsType, value: string) => {
    onChange({ [field]: value })
  }

  return (
    <Accordion
      type="single"
      collapsible
      value={expanded}
      onValueChange={setExpanded}
      className={`w-full transition-all duration-300 ${
        isOtherProfile ? "ring-2 ring-warning/20 rounded-lg shadow-sm" : ""
      }`}
    >
      <AccordionItem value="advanced-options" className="border-none">
        <AccordionTrigger
          className={`text-base font-medium px-4 hover:no-underline transition-colors ${
            isOtherProfile ? "bg-warning/5 hover:bg-warning/10" : "hover:bg-accent/50"
          }`}
        >
          <div className="flex items-center gap-3 flex-1">
            <span>Advanced Options</span>
            {isOtherProfile && (
              <Badge
                variant={allRequiredFieldsFilled ? "default" : "destructive"}
                className="ml-2 gap-1 transition-all duration-300"
              >
                {allRequiredFieldsFilled ? (
                  <>
                    <CheckCircle2 className="h-3 w-3" />
                    <span className="text-xs">Complete</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-3 w-3" />
                    <span className="text-xs">Required</span>
                  </>
                )}
              </Badge>
            )}
          </div>
        </AccordionTrigger>
        <AccordionContent className="space-y-6 pt-6 px-4 pb-4">
          {hasRequiredFields && (
            <Alert variant="destructive" className="border-warning bg-warning/10">
              <AlertTriangle className="h-5 w-5 text-warning" />
              <AlertDescription className="text-sm font-medium text-foreground ml-2">
                <span className="font-semibold">Required for 'Other' profile:</span> Custom width, height, and output
                format (cannot be 'Auto')
              </AlertDescription>
            </Alert>
          )}

          {isOtherProfile && allRequiredFieldsFilled && (
            <Alert variant="success">
              <CheckCircle2 className="h-5 w-5" />
              <AlertDescription className="text-sm font-medium ml-2">
                All required fields configured correctly
              </AlertDescription>
            </Alert>
          )}

          {/* Custom Profile Options */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold">Custom Profile Options</h3>
              {isOtherProfile && (
                <Badge variant="outline" className="text-xs">
                  Required for Other
                </Badge>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label
                    htmlFor="custom-width"
                    className={`font-medium ${
                      isOtherProfile && !hasCustomWidth
                        ? "text-warning"
                        : hasCustomWidth && isOtherProfile
                          ? "text-success"
                          : ""
                    }`}
                  >
                    Custom Width
                    {isOtherProfile && <span className="text-destructive ml-1">*</span>}
                  </Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="h-4 w-4 text-muted-foreground" aria-label="Help about custom width" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Custom screen width in pixels{isOtherProfile ? " (required for Other profile)" : ""}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  {hasCustomWidth && isOtherProfile && <CheckCircle2 className="h-4 w-4 text-success ml-auto" />}
                </div>
                <Input
                  id="custom-width"
                  type="number"
                  value={options.customWidth || ""}
                  onChange={(e) => handleNumberChange("customWidth", e.target.value)}
                  min={1}
                  placeholder="e.g., 1072"
                  aria-label="Custom screen width"
                  className={`transition-all duration-200 ${
                    isOtherProfile && !hasCustomWidth
                      ? "border-warning focus-visible:ring-warning"
                      : hasCustomWidth && isOtherProfile
                        ? "border-success focus-visible:ring-success"
                        : ""
                  }`}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label
                    htmlFor="custom-height"
                    className={`font-medium ${
                      isOtherProfile && !hasCustomHeight
                        ? "text-warning"
                        : hasCustomHeight && isOtherProfile
                          ? "text-success"
                          : ""
                    }`}
                  >
                    Custom Height
                    {isOtherProfile && <span className="text-destructive ml-1">*</span>}
                  </Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="h-4 w-4 text-muted-foreground" aria-label="Help about custom height" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Custom screen height in pixels{isOtherProfile ? " (required for Other profile)" : ""}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  {hasCustomHeight && isOtherProfile && <CheckCircle2 className="h-4 w-4 text-success ml-auto" />}
                </div>
                <Input
                  id="custom-height"
                  type="number"
                  value={options.customHeight || ""}
                  onChange={(e) => handleNumberChange("customHeight", e.target.value)}
                  min={1}
                  placeholder="e.g., 1448"
                  aria-label="Custom screen height"
                  className={`transition-all duration-200 ${
                    isOtherProfile && !hasCustomHeight
                      ? "border-warning focus-visible:ring-warning"
                      : hasCustomHeight && isOtherProfile
                        ? "border-success focus-visible:ring-success"
                        : ""
                  }`}
                />
              </div>
            </div>
          </div>

          {/* Main Options */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Main Options</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <OptionCheckbox
                  id="manga-style"
                  label="Manga Style"
                  checked={isMangaMode}
                  onCheckedChange={() => {}}
                  tooltip="Right-to-left reading and splitting"
                  contentType={contentType}
                  disabled={true}
                  notice={
                    isMangaMode
                      ? "Want to convert a comic? Switch to Comic mode"
                      : "Want to convert a manga? Switch to Manga mode"
                  }
                  setMode={setMode}
                />
                <OptionCheckbox
                  id="hq"
                  label="High Quality"
                  checked={options.hq}
                  onCheckedChange={() => handleCheckboxChange("hq")}
                  tooltip="Try to increase the quality of magnification"
                  contentType={contentType}
                />
                <OptionCheckbox
                  id="two-panel"
                  label="Two Panel"
                  checked={options.twoPanel}
                  onCheckedChange={() => handleCheckboxChange("twoPanel")}
                  tooltip="Display two not four panels in Panel View mode"
                  contentType={contentType}
                />
              </div>
              <div className="space-y-4">
                <OptionCheckbox
                  id="webtoon"
                  label="Webtoon"
                  checked={options.webtoon}
                  onCheckedChange={() => handleCheckboxChange("webtoon")}
                  tooltip="Webtoon processing mode"
                  contentType={contentType}
                />
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="target-size">Target Size (MB)</Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-muted-foreground" aria-label="Help about target size" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Maximum size of output file in MB</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Input
                    id="target-size"
                    type="number"
                    value={options.targetSize}
                    onChange={(e) => handleNumberChange("targetSize", e.target.value)}
                    min={1}
                    aria-label="Target size in megabytes"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Processing Options */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Processing Options</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <OptionCheckbox
                  id="no-processing"
                  label="No Processing"
                  checked={options.noProcessing}
                  onCheckedChange={() => handleCheckboxChange("noProcessing")}
                  tooltip="Do not modify image"
                  contentType={contentType}
                />
                <OptionCheckbox
                  id="upscale"
                  label="Upscale"
                  checked={options.upscale}
                  onCheckedChange={() => handleCheckboxChange("upscale")}
                  tooltip="Resize images smaller than device's resolution"
                  contentType={contentType}
                />
                <OptionCheckbox
                  id="stretch"
                  label="Stretch"
                  checked={options.stretch}
                  onCheckedChange={() => handleCheckboxChange("stretch")}
                  tooltip="Stretch images to device's resolution"
                  contentType={contentType}
                />
              </div>
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="splitter">Splitter Mode</Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-muted-foreground" aria-label="Help about splitter mode" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Double page parsing mode</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Select
                    value={options.splitter.toString()}
                    onValueChange={(value) => handleSelectChange("splitter", value)}
                    aria-label="Select splitter mode"
                  >
                    <SelectTrigger id="splitter">
                      <SelectValue placeholder="Select splitter mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">Split</SelectItem>
                      <SelectItem value="1">Rotate</SelectItem>
                      <SelectItem value="2">Both</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="gamma">Gamma</Label>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle
                            className="h-4 w-4 text-muted-foreground"
                            aria-label="Help about gamma correction"
                          />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Apply gamma correction (0 for Auto)</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                  <Input
                    id="gamma"
                    type="number"
                    value={options.gamma}
                    onChange={(e) => handleNumberChange("gamma", e.target.value)}
                    step={0.1}
                    min={0}
                    aria-label="Gamma correction value"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Output Settings */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Output Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label
                    htmlFor="output-format"
                    className={`font-medium ${
                      isOtherProfile && !hasValidOutputFormat
                        ? "text-warning"
                        : hasValidOutputFormat && isOtherProfile
                          ? "text-success"
                          : ""
                    }`}
                  >
                    Output Format
                    {isOtherProfile && <span className="text-destructive ml-1">*</span>}
                  </Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <HelpCircle className="h-4 w-4 text-muted-foreground" aria-label="Help about output format" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>
                          Select output format{isOtherProfile ? " (required for Other profile, cannot be Auto)" : ""}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  {hasValidOutputFormat && isOtherProfile && <CheckCircle2 className="h-4 w-4 text-success ml-auto" />}
                </div>
                <Select
                  value={options.outputFormat}
                  onValueChange={(value) => handleSelectChange("outputFormat", value)}
                  aria-label="Select output format"
                >
                  <SelectTrigger
                    id="output-format"
                    className={`transition-all duration-200 ${
                      isOtherProfile && !hasValidOutputFormat
                        ? "border-warning focus:ring-warning"
                        : hasValidOutputFormat && isOtherProfile
                          ? "border-success focus:ring-success"
                          : ""
                    }`}
                  >
                    <SelectValue placeholder="Select output format" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Auto">Auto</SelectItem>
                    <SelectItem value="MOBI">MOBI</SelectItem>
                    <SelectItem value="EPUB">EPUB</SelectItem>
                    <SelectItem value="CBZ">CBZ</SelectItem>
                    <SelectItem value="KFX">KFX</SelectItem>
                    <SelectItem value="MOBI+EPUB">MOBI+EPUB</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="author">Author</Label>
                  <Input
                    id="author"
                    value={options.author}
                    onChange={(e) => handleTextChange("author", e.target.value)}
                    aria-label="Author name"
                  />
                </div>
                <OptionCheckbox
                  id="no-kepub"
                  label="No Kepub"
                  checked={options.noKepub}
                  onCheckedChange={() => handleCheckboxChange("noKepub")}
                  tooltip="Use .epub extension instead of .kepub.epub"
                  contentType={contentType}
                />
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}

interface OptionCheckboxProps {
  id: string
  label: string
  checked: boolean
  onCheckedChange: () => void
  tooltip: string
  contentType?: "comic" | "manga"
  disabled?: boolean
  notice?: string
  setMode?: (mode: "comic" | "manga") => void
}

function OptionCheckbox({
  id,
  label,
  checked,
  onCheckedChange,
  tooltip,
  contentType = "manga",
  disabled = false,
  notice,
  setMode,
}: OptionCheckboxProps) {
  const isComic = contentType === "comic"
  const checkboxClassName = isComic
    ? "!border-theme-medium data-[state=checked]:!bg-theme-medium data-[state=checked]:!border-theme-medium focus-visible:!ring-theme-medium"
    : "!border-theme-dark data-[state=checked]:!bg-theme-dark data-[state=checked]:!border-theme-dark focus-visible:!ring-theme-dark"

  const renderNotice = () => {
    if (!notice) return null

    // Check if notice contains "Switch to Comic mode" or "Switch to Manga mode"
    const comicMatch = notice.match(/(.*?)(Switch to Comic mode)(.*)/i)
    const mangaMatch = notice.match(/(.*?)(Switch to Manga mode)(.*)/i)

    if (comicMatch && setMode) {
      return (
        <p className="text-xs text-muted-foreground ml-6 italic">
          {comicMatch[1]}
          <button
            type="button"
            onClick={() => setMode("comic")}
            className="text-primary hover:text-primary/80 underline underline-offset-2 cursor-pointer font-medium transition-colors"
          >
            {comicMatch[2]}
          </button>
          {comicMatch[3]}
        </p>
      )
    }

    if (mangaMatch && setMode) {
      return (
        <p className="text-xs text-muted-foreground ml-6 italic">
          {mangaMatch[1]}
          <button
            type="button"
            onClick={() => setMode("manga")}
            className="text-primary hover:text-primary/80 underline underline-offset-2 cursor-pointer font-medium transition-colors"
          >
            {mangaMatch[2]}
          </button>
          {mangaMatch[3]}
        </p>
      )
    }

    // Fallback to plain text if no match
    return <p className="text-xs text-muted-foreground ml-6 italic">{notice}</p>
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center space-x-2">
        <Checkbox
          id={id}
          checked={checked}
          onCheckedChange={onCheckedChange}
          aria-label={label}
          className={checkboxClassName}
          disabled={disabled}
        />
        <div className="flex items-center gap-2">
          <Label htmlFor={id} className={`cursor-pointer ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}>
            {label}
          </Label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle
                  className="h-4 w-4 text-muted-foreground"
                  aria-label={`Help about ${label.toLowerCase()}`}
                />
              </TooltipTrigger>
              <TooltipContent>
                <p>{tooltip}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
      {renderNotice()}
    </div>
  )
}
