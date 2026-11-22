import * as React from "react"
import { Highlight, HighlightItem } from "@animate-ui/react/primitives/effects/highlight"

function HoverHighlight({ children }: { children: React.ReactNode }) {
  return (
    <Highlight controlledItems hover click={false} className="inset-0 rounded-md bg-muted">
      {children}
    </Highlight>
  )
}

function HoverItem({
  as = "li",
  className,
  children,
}: {
  as?: "li" | "div"
  className?: string
  children: React.ReactElement
}) {
  return (
    <HighlightItem as={as} className={className}>
      {children}
    </HighlightItem>
  )
}

export { HoverHighlight, HoverItem }
