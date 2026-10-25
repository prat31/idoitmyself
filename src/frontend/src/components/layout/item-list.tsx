import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

/** A stacked list of full-width rows (Inboxes, Filters, Labels, Scans): one container, hairline dividers. */
export function ItemList({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <ul className={cn('divide-y overflow-hidden rounded-xl border bg-card shadow-xs', className)}>
      {children}
    </ul>
  )
}

type ItemRowProps = {
  /** Leading identity mark (icon tile, colour dot). */
  leading?: ReactNode
  title: ReactNode
  /** Badges next to the title (provider, status). */
  badges?: ReactNode
  /** Right-aligned key figures; drops below the text on phones. */
  figures?: ReactNode
  /** Row actions (edit, delete); kept above any stretched link. */
  actions?: ReactNode
  /** Secondary lines under the title. */
  children?: ReactNode
  /** Small muted metadata line at the bottom. */
  meta?: ReactNode
  className?: string
}

/** One row: title + badges, description lines and a meta line on the left; figures and actions on the
 *  right. Modeled on dense model/catalog listings — tabular rhythm without a table. */
export function ItemRow({ leading, title, badges, figures, actions, children, meta, className }: ItemRowProps) {
  return (
    <li className={cn('relative flex gap-3 px-4 py-4 transition-colors hover:bg-accent/40 sm:gap-4 sm:px-5', className)}>
      {leading && <div className="shrink-0 pt-0.5">{leading}</div>}
      <div className="flex min-w-0 flex-1 flex-col gap-3 md:flex-row md:items-start md:gap-6">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className="min-w-0 truncate text-sm font-semibold">{title}</h3>
            {badges}
          </div>
          {children}
          {meta && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-0.5 text-xs text-muted-foreground">{meta}</div>
          )}
        </div>
        {figures && <div className="flex shrink-0 items-start gap-5 md:justify-end">{figures}</div>}
      </div>
      {actions && <div className="relative z-10 -mr-1.5 -mt-1 flex shrink-0 items-start">{actions}</div>}
    </li>
  )
}

/** A right-aligned figure: value over a small caption. */
export function Figure({ value, label, muted }: { value: ReactNode; label: string; muted?: boolean }) {
  return (
    <div className="min-w-14 text-left md:text-right">
      <div className={cn('text-sm font-semibold tabular-nums', muted && 'text-muted-foreground')}>{value}</div>
      <div className="text-[11px] text-muted-foreground">{label}</div>
    </div>
  )
}

/** Separator dot for meta lines. */
export function MetaDot() {
  return <span aria-hidden="true" className="text-muted-foreground/50">·</span>
}
