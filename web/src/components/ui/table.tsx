import * as React from "react"
import { cn } from "cn"
import { Highlight, HighlightItem } from "@animate-ui/react/primitives/effects/highlight"

// Hàng trong TableBody được highlight khi hover (mode "parent": nền là một div đặt NGOÀI <table>, trong vùng chứa,
// nên không chèn div vào tbody/tr). Hàng ở thead không bọc nên không có hiệu ứng.
const InTableBody = React.createContext(false)

function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div
      data-slot="table-container"
      className="relative w-full overflow-x-auto"
    >
      <Highlight mode="parent" controlledItems hover click={false} className="rounded-md bg-muted/60">
        <table
          data-slot="table"
          className={cn("w-full caption-bottom text-sm", className)}
          {...props}
        />
      </Highlight>
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b", className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <InTableBody.Provider value={true}>
      <tbody
        data-slot="table-body"
        className={cn("[&_tr:last-child]:border-0", className)}
        {...props}
      />
    </InTableBody.Provider>
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        "border-t bg-muted/50 font-medium [&>tr]:last:border-b-0",
        className
      )}
      {...props}
    />
  )
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  const inBody = React.useContext(InTableBody)
  const row = (
    <tr
      data-slot="table-row"
      className={cn(
        "border-b transition-colors has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted",
        !inBody && "hover:bg-muted/50",
        className
      )}
      {...props}
    />
  )
  return inBody ? <HighlightItem asChild>{row}</HighlightItem> : row
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "h-10 px-2 text-left align-middle font-medium whitespace-nowrap text-foreground [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        "p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("mt-4 text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}
