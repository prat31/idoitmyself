import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'

export type BarListItem = {
  key: string
  label: string
  /** Muted secondary text after the label (e.g. an email address). */
  sublabel?: string
  value: number
  /** Leading identity mark (e.g. a label's colour dot). Text never takes the data colour. */
  icon?: ReactNode
  href?: string
  title?: string
  mono?: boolean
}

/** Ranked horizontal bars, one neutral hue (magnitude, not identity), value labelled at the tip. */
export function BarList({ items, emptyText = 'Nothing to show' }: { items: BarListItem[]; emptyText?: string }) {
  const max = Math.max(0, ...items.map((i) => i.value))
  if (items.length === 0) return <p className="py-6 text-center text-sm text-muted-foreground">{emptyText}</p>

  return (
    <ul className="space-y-2.5">
      {items.map((item) => {
        const row = (
          <>
            <div className="mb-1 flex items-center gap-2 text-sm">
              {item.icon}
              <span className={cn('min-w-0 flex-1 truncate', item.mono && 'font-mono text-[13px]')} title={item.title ?? item.label}>
                {item.label}
                {item.sublabel && <span className="ml-1.5 text-xs text-muted-foreground">{item.sublabel}</span>}
              </span>
              <span className="shrink-0 font-medium tabular-nums">{formatNumber(item.value)}</span>
            </div>
            <div className="h-2 rounded-full bg-muted" aria-hidden="true">
              <div
                className="h-full rounded-full bg-chart-emphasis transition-[width] duration-500"
                style={{ width: max ? `${Math.max(item.value ? 1.5 : 0, (item.value / max) * 100)}%` : 0 }}
              />
            </div>
          </>
        )
        return (
          <li key={item.key}>
            {item.href ? (
              <Link
                to={item.href}
                className="-mx-2 block rounded-md px-2 py-1 outline-none transition-colors hover:bg-accent/60 focus-visible:ring-2 focus-visible:ring-ring/50"
              >
                {row}
              </Link>
            ) : (
              <div className="py-1">{row}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
