import * as React from "react"
import { Highlight, HighlightItem } from "@animate-ui/react/primitives/effects/highlight"

// Nền trượt theo con trỏ trong một danh sách. Bọc quanh <ul>/<ol>; mỗi mục là <HoverItem><li>…</li></HoverItem>.
// Primitive tự tôn trọng prefers-reduced-motion (ReducedMotionConfig nằm trong Highlight).
function HoverHighlight({ children }: { children: React.ReactNode }) {
  return (
    <Highlight controlledItems hover click={false} className="rounded-md bg-muted">
      {children}
    </Highlight>
  )
}

// asChild: giữ nguyên thẻ con (li, div) làm phần tử của danh sách, không chèn div thừa.
function HoverItem({ children }: { children: React.ReactElement }) {
  return <HighlightItem asChild>{children}</HighlightItem>
}

export { HoverHighlight, HoverItem }
