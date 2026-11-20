import * as React from "react"
import { Highlight, HighlightItem } from "@animate-ui/react/primitives/effects/highlight"

// Nền trượt theo con trỏ trong một danh sách. Bọc quanh <ul>/<ol>; mỗi mục là <HoverItem>một phần tử</HoverItem>.
// Primitive tự tôn trọng prefers-reduced-motion (ReducedMotionConfig nằm trong Highlight).
function HoverHighlight({ children }: { children: React.ReactNode }) {
  return (
    <Highlight controlledItems hover click={false} className="inset-0 rounded-md bg-muted">
      {children}
    </Highlight>
  )
}

// Vỏ của một mục, mặc định là <li>; con phải là ĐÚNG MỘT phần tử (thư viện clone nó để đặt z-index trên nền).
// Không dùng asChild vì bản asChild của thư viện lồng chính phần tử con vào bên trong chính nó (li trong li).
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
