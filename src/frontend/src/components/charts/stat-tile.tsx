import type { ReactNode } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router'

import { cn } from '@/lib/utils'

const tileClass = 'min-w-0 rounded-xl border bg-card px-4 py-3.5 shadow-xs'
const interactiveClass =
  'group block w-full text-left transition-colors outline-none hover:bg-accent/40 focus-visible:ring-[3px] focus-visible:ring-ring/50'

/** Headline number: label · value · optional hint. With `href` it opens that page; with `onClick` it
 *  acts as a button (e.g. opens a detail window). */
export function StatTile({
  label,
  value,
  hint,
  href,
  onClick,
  className,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  href?: string
  onClick?: () => void
  className?: string
}) {
  const body = (
    <>
      <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
        <span className="truncate">{label}</span>
        {(href || onClick) && (
          <ArrowUpRight
            className="ml-auto size-3.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
            aria-hidden="true"
          />
        )}
      </p>
      <p className="mt-1 truncate text-2xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</p>}
    </>
  )
  if (href) {
    return (
      <Link to={href} className={cn(tileClass, interactiveClass, className)}>
        {body}
      </Link>
    )
  }
  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(tileClass, interactiveClass, className)}>
        {body}
      </button>
    )
  }
  return <div className={cn(tileClass, className)}>{body}</div>
}
