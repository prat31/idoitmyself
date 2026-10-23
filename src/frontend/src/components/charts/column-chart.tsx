import { useEffect, useRef, useState } from 'react'

import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import { formatTick, niceTicks } from './scale'

export type ColumnSeries = {
  key: string
  label: string
  /** Tailwind bg class for the segment, e.g. 'bg-chart-emphasis'. */
  className: string
}

export type ColumnDatum = {
  key: string
  /** Short axis label (e.g. "17 Oct"), and a fuller one for the tooltip. */
  label: string
  title: string
  values: Record<string, number>
}

const PLOT_HEIGHT = 176

/** Stacked columns over time. Series stack bottom→top in the given order; the whole column slot is the
 *  hover/focus target and shows every series' value. */
export function ColumnChart({ data, series }: { data: ColumnDatum[]; series: ColumnSeries[] }) {
  const [active, setActive] = useState<number | null>(null)
  // Show as many x labels as fit (~56px each) at the chart's actual width, so they never collide.
  const plotRef = useRef<HTMLDivElement>(null)
  const [plotWidth, setPlotWidth] = useState(0)
  useEffect(() => {
    const node = plotRef.current
    if (!node) return
    const observer = new ResizeObserver(([entry]) => setPlotWidth(entry.contentRect.width))
    observer.observe(node)
    return () => observer.disconnect()
  }, [])
  const totals = data.map((d) => series.reduce((sum, s) => sum + (d.values[s.key] ?? 0), 0))
  const ticks = niceTicks(Math.max(0, ...totals))
  const top = ticks[ticks.length - 1]
  const maxLabels = plotWidth ? Math.max(2, Math.floor(plotWidth / 56)) : 8
  const labelEvery = Math.max(1, Math.ceil(data.length / maxLabels))
  const hovered = active !== null ? data[active] : null

  return (
    <div className="relative pt-2">
      <div className="flex gap-2">
        {/* Y axis */}
        <div className="relative w-7 shrink-0 text-right text-[10px] tabular-nums text-muted-foreground" style={{ height: PLOT_HEIGHT }}>
          {ticks.map((tick) => (
            <span key={tick} className="absolute right-0 -translate-y-1/2" style={{ bottom: `${(tick / top) * 100}%` }}>
              {formatTick(tick)}
            </span>
          ))}
        </div>

        <div ref={plotRef} className="min-w-0 flex-1">
          {/* Plot */}
          <div className="relative" style={{ height: PLOT_HEIGHT }} onPointerLeave={() => setActive(null)}>
            {ticks.map((tick) => (
              <div
                key={tick}
                className={cn('absolute inset-x-0 h-px', tick === 0 ? 'bg-border' : 'bg-chart-grid')}
                style={{ bottom: `${(tick / top) * 100}%` }}
                aria-hidden="true"
              />
            ))}
            <div className="absolute inset-0 flex items-end">
              {data.map((datum, i) => (
                <button
                  key={datum.key}
                  type="button"
                  aria-label={`${datum.title}: ${series.map((s) => `${s.label} ${datum.values[s.key] ?? 0}`).join(', ')}`}
                  onPointerEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  className={cn(
                    'group relative flex h-full min-w-0 flex-1 flex-col items-center justify-end rounded-sm outline-none',
                    active === i && 'bg-muted/60',
                    'focus-visible:ring-2 focus-visible:ring-ring/50',
                  )}
                >
                  <span className="flex w-[70%] max-w-6 flex-col-reverse gap-[2px]">
                    {series.map((s, si) => {
                      const value = datum.values[s.key] ?? 0
                      if (!value) return null
                      const isTop = series.slice(si + 1).every((later) => !(datum.values[later.key] ?? 0))
                      return (
                        <span
                          key={s.key}
                          className={cn('block w-full', s.className, isTop && 'rounded-t-[4px]')}
                          style={{ height: `${(value / top) * PLOT_HEIGHT}px` }}
                        />
                      )
                    })}
                  </span>
                </button>
              ))}
            </div>

            {/* Tooltip */}
            {hovered && active !== null && (
              <div
                className="pointer-events-none absolute top-0 z-10 min-w-36 rounded-lg border bg-popover px-3 py-2 text-xs shadow-md"
                style={{
                  left: `${((active + 0.5) / data.length) * 100}%`,
                  transform: `translateX(${active / data.length > 0.6 ? '-105%' : '5%'})`,
                }}
              >
                <p className="mb-1 text-muted-foreground">{hovered.title}</p>
                {[...series].reverse().map((s) => (
                  <p key={s.key} className="flex items-center gap-2">
                    <span className={cn('h-0.5 w-3 rounded-full', s.className)} aria-hidden="true" />
                    <span className="font-semibold tabular-nums">{formatNumber(hovered.values[s.key] ?? 0)}</span>
                    <span className="text-muted-foreground">{s.label}</span>
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* X axis */}
          <div className="mt-1.5 flex text-[10px] text-muted-foreground">
            {data.map((datum, i) => (
              <span key={datum.key} className="min-w-0 flex-1 overflow-visible text-center whitespace-nowrap">
                {i % labelEvery === 0 ? datum.label : ''}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
