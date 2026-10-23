import { formatDate } from '@/lib/format'
import { labelColorClass } from '@/features/labels/colors'
import { cn } from '@/lib/utils'
import type { DashboardCoverage } from './api'

/** Per label: the stretch from the earliest scan to today, with covered ranges filled and gaps empty. */
export function CoverageStrip({ data }: { data: DashboardCoverage }) {
  if (!data.span_start || data.labels.length === 0) {
    return <p className="rounded-xl border border-dashed px-5 py-8 text-center text-sm text-muted-foreground">No completed runs yet.</p>
  }
  const from = new Date(data.span_start).getTime()
  const to = new Date(data.span_end).getTime()
  const span = Math.max(1, to - from)
  const pct = (t: string) => `${((Math.min(to, Math.max(from, new Date(t).getTime())) - from) / span) * 100}%`

  return (
    <div className="rounded-xl border bg-card p-4 shadow-xs sm:p-5">
      <ul className="space-y-3">
        {data.labels.map((label) => {
          const covered = label.covered.map((c) => `${formatDate(c.start)} – ${formatDate(new Date(new Date(c.end).getTime() - 1))}`)
          return (
            <li key={label.label_id} className="grid gap-1.5 sm:grid-cols-[10rem_1fr] sm:items-center sm:gap-4">
              <span className="flex min-w-0 items-center gap-1.5 text-sm">
                <span className={cn('size-2 shrink-0 rounded-full', labelColorClass[label.color])} aria-hidden="true" />
                <span className="truncate font-mono">{label.name}</span>
              </span>
              <div
                className="relative h-3 overflow-hidden rounded-full bg-muted"
                role="img"
                aria-label={covered.length ? `Covered: ${covered.join('; ')}` : 'Not covered'}
                title={covered.length ? covered.join('\n') : 'Not covered by a completed run with the current condition'}
              >
                {label.covered.map((c) => (
                  <span
                    key={c.start}
                    className="absolute inset-y-0 rounded-full bg-chart-emphasis"
                    style={{ left: pct(c.start), width: `calc(${pct(c.end)} - ${pct(c.start)})` }}
                  />
                ))}
              </div>
            </li>
          )
        })}
      </ul>
      <div className="mt-2 flex justify-between text-[11px] text-muted-foreground sm:ml-[11rem]">
        <span>{formatDate(data.span_start)}</span>
        <span>Today</span>
      </div>
    </div>
  )
}
