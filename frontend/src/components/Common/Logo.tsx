import { Link } from "@tanstack/react-router"
import { BookOpenText } from "lucide-react"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  size?: "default" | "large"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  size = "default",
  className,
  asLink = true,
}: LogoProps) {
  const isLarge = size === "large"

  const content = (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "flex shrink-0 items-center justify-center bg-foreground text-background",
          isLarge ? "size-12 rounded-lg" : "size-8 rounded-md",
        )}
      >
        <BookOpenText className={isLarge ? "size-7" : "size-5"} aria-hidden />
      </span>

      {variant !== "icon" && (
        <span
          className={cn(
            "whitespace-nowrap font-semibold",
            isLarge ? "text-2xl" : "text-lg",
            variant === "responsive" && "group-data-[collapsible=icon]:hidden",
          )}
        >
          TechDoc AI
        </span>
      )}
    </span>
  )

  if (!asLink) {
    return content
  }

  return (
    <Link to="/" aria-label="TechDoc AI 首页">
      {content}
    </Link>
  )
}
