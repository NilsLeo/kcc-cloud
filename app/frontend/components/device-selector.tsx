"use client"

import React from "react"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { HelpCircle, Smartphone } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface DeviceSelectorProps {
  selectedProfile: string
  onProfileChange: (profile: string) => void
  deviceProfiles: Record<string, string>
}

export function DeviceSelector({ selectedProfile, onProfileChange, deviceProfiles }: DeviceSelectorProps) {
  // Group device profiles by brand
  const groupedProfiles: Record<string, Record<string, string>> = {
    Kindle: {},
    Kobo: {},
    reMarkable: {},
    Other: {},
  }

  Object.entries(deviceProfiles).forEach(([key, value]) => {
    if (key === "Placeholder") return

    if (key.startsWith("K") && !key.startsWith("Ko")) {
      groupedProfiles["Kindle"][key] = value
    } else if (key.startsWith("Ko")) {
      groupedProfiles["Kobo"][key] = value
    } else if (key.startsWith("Rmk")) {
      groupedProfiles["reMarkable"][key] = value
    } else {
      groupedProfiles["Other"][key] = value
    }
  })

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Smartphone className="h-5 w-5 text-muted-foreground" />
        <label htmlFor="device-selector" className="text-base font-medium">
          Select Your E-Reader
        </label>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <HelpCircle className="h-4 w-4 text-muted-foreground" aria-label="Help" />
            </TooltipTrigger>
            <TooltipContent>
              <p>Select your device profile for optimal conversion settings</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <Select value={selectedProfile} onValueChange={onProfileChange} aria-label="Select your e-reader device">
        <SelectTrigger id="device-selector" className="w-full">
          <SelectValue placeholder="Select your E-Reader" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="Placeholder" disabled>
            Please Select your E-Reader
          </SelectItem>

          {Object.entries(groupedProfiles).map(
            ([brand, devices]) =>
              Object.keys(devices).length > 0 && (
                <React.Fragment key={brand}>
                  <SelectItem value={`${brand}-header`} disabled className="font-semibold text-muted-foreground">
                    {brand} Devices
                  </SelectItem>
                  {Object.entries(devices).map(([key, value]) => (
                    <SelectItem key={key} value={key} className="pl-6">
                      {value}
                    </SelectItem>
                  ))}
                </React.Fragment>
              ),
          )}
        </SelectContent>
      </Select>
    </div>
  )
}
