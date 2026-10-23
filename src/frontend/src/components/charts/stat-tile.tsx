import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/** Headline number: label · value · optional hint. */
export function StatTile({
  label,
  value,
  hint,
  className,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('min-w-0 rounded-xl border bg-card px-4 py-3.5 shadow-xs', className)}>
      <p className="truncate text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-2xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-0.5 truncate text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}
