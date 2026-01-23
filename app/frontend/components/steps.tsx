import React from "react"
import { cn } from "@/lib/utils"
import { CheckCircle2 } from "lucide-react"

interface StepsProps {
  currentStep: number
  children: React.ReactNode
  className?: string
}

interface StepProps {
  title: string
  description?: string
}

export function Steps({ currentStep, children, className }: StepsProps) {
  const steps = React.Children.toArray(children) as React.ReactElement<StepProps>[]

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isActive = currentStep === index + 1
          const isCompleted = currentStep > index + 1

          return (
            <React.Fragment key={index}>
              {/* Step */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors",
                    isActive && "border-primary bg-primary text-primary-foreground",
                    isCompleted && "border-primary bg-primary text-primary-foreground",
                    !isActive && !isCompleted && "border-muted-foreground text-muted-foreground",
                  )}
                >
                  {isCompleted ? <CheckCircle2 className="w-6 h-6" /> : <span>{index + 1}</span>}
                </div>
                <div className="mt-2 text-center">
                  <div
                    className={cn(
                      "text-sm font-medium",
                      isActive && "text-foreground",
                      isCompleted && "text-foreground",
                      !isActive && !isCompleted && "text-muted-foreground",
                    )}
                  >
                    {step.props.title}
                  </div>
                  {step.props.description && (
                    <div
                      className={cn(
                        "text-xs mt-1",
                        isActive && "text-muted-foreground",
                        isCompleted && "text-muted-foreground",
                        !isActive && !isCompleted && "text-muted-foreground/60",
                      )}
                    >
                      {step.props.description}
                    </div>
                  )}
                </div>
              </div>

              {/* Connector */}
              {index < steps.length - 1 && (
                <div className={cn("flex-1 h-0.5 mx-2", index < currentStep - 1 ? "bg-primary" : "bg-muted")} />
              )}
            </React.Fragment>
          )
        })}
      </div>
    </div>
  )
}

export function Step({ title, description }: StepProps) {
  return null // This component is just for type-checking and props
}
