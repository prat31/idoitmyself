import { useState, type ReactNode } from 'react'
import { BarChart3, Table2 } from 'lucide-react'

import { cn } from '@/lib/utils'

export type LegendItem = { label: string; swatchClass: string }

type ChartCardProps = {
  title: string
  description?: string
  legend?: LegendItem[]
  /** The chart. */
  children: ReactNode
  /** The accessible table twin of the chart; enables the Chart/Table toggle. */
  table?: ReactNode
  /** Dim while refetching, keeping the previous render in place. */
  stale?: boolean
  className?: string
}

/** A chart's frame: title, legend, and a Chart ↔ Table toggle so every value is reachable without hover. */
export function ChartCard({ title, description, legend, children, table, stale, className }: ChartCardProps) {
  const [view, setView] = useState<'chart' | 'table'>('chart')

  return (
    <figure className={cn('flex min-w-0 flex-col rounded-xl border bg-card shadow-xs', className)}>
      <figcaption className="flex flex-wrap items-start gap-x-4 gap-y-2 px-4 pt-4 sm:px-5">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-medium">{title}</h3>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
        {table && (
          <div className="flex rounded-md border p-0.5" role="group" aria-label={`${title} view`}>
            {(['chart', 'table'] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={view === option}
                aria-label={option === 'chart' ? 'Show chart' : 'Show table'}
                onClick={() => setView(option)}
                className={cn(
                  'rounded-[5px] p-1 text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
                  view === option ? 'bg-secondary text-foreground' : 'hover:text-foreground',
                )}
              >
                {option === 'chart' ? <BarChart3 className="size-3.5" /> : <Table2 className="size-3.5" />}
              </button>
            ))}
          </div>
        )}
      </figcaption>
      {legend && legend.length > 1 && view === 'chart' && (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 px-4 pt-2 text-xs text-muted-foreground sm:px-5">
          {legend.map((item) => (
            <li key={item.label} className="flex items-center gap-1.5">
              <span className={cn('size-2.5 rounded-[3px]', item.swatchClass)} aria-hidden="true" />
              {item.label}
            </li>
          ))}
        </ul>
      )}
      <div className={cn('min-w-0 flex-1 px-4 pb-4 pt-3 transition-opacity sm:px-5', stale && 'opacity-60')}>
        {view === 'table' && table ? table : children}
      </div>
    </figure>
  )
}

/** Minimal table used as a chart's table view. */
export function ChartTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  return (
    <div className="max-h-80 overflow-auto rounded-md border">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-muted text-xs text-muted-foreground">
          <tr>
            {columns.map((column, i) => (
              <th key={column} className={cn('px-3 py-2 font-medium', i === 0 ? 'text-left' : 'text-right')}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, i) => (
                <td key={i} className={cn('px-3 py-1.5', i === 0 ? 'text-left' : 'text-right tabular-nums')}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
