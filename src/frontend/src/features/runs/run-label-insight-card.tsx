import { Filter, TriangleAlert } from 'lucide-react'

import { BarList } from '@/components/charts/bar-list'
import { ChartCard, ChartTable } from '@/components/charts/chart-card'
import { labelColorClass } from '@/features/labels/colors'
import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { RunLabelInsight } from './api'

const bucketLabel = (start: number) => `${start.toFixed(1)}–${(start + 0.1).toFixed(1)}`

/** One label in a run: the condition and threshold it was asked with, answer counts, and how the
 *  model's probabilities were distributed (counts labelled on every bucket — the spread is usually
 *  very skewed, so values are read from the labels, not bar lengths). */
export function RunLabelInsightCard({ insight, nearWindow }: { insight: RunLabelInsight; nearWindow: number }) {
  const t = insight.match_threshold
  return (
    <ChartCard
      title={insight.label_name}
      description={`Answers from this run · match ≥ ${t.toFixed(2)}`}
      table={
        <ChartTable
          columns={['Probability', 'Answers']}
          rows={insight.histogram.map((b) => [bucketLabel(b.start), b.count])}
        />
      }
    >
      <div className="space-y-4">
        <div className="space-y-1.5">
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
            <Filter className="mt-0.5 size-3 shrink-0" aria-label="Filter condition as asked" />
            <span className="line-clamp-3">{insight.filter_condition}</span>
          </p>
          {insight.condition_changed && (
            <p className="inline-flex items-center gap-1.5 rounded-md bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
              <TriangleAlert className="size-3.5" />
              {insight.label_id ? "The label's condition has changed since this run" : 'Label deleted since this run'}
            </p>
          )}
        </div>

        <dl className="grid grid-cols-3 gap-3 text-center">
          {[
            ['Asked', insight.asked],
            ['Matched', insight.matched],
            [`Within ±${nearWindow}`, insight.near_threshold],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-muted/50 px-2 py-2">
              <dd className="text-base font-semibold tabular-nums">{formatNumber(value as number)}</dd>
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
            </div>
          ))}
        </dl>

        {insight.asked === 0 ? (
          <p className="text-sm text-muted-foreground">
            No per-email answers are attributed to this run (it predates stored answers, or later runs re-asked these
            emails).
          </p>
        ) : (
          <BarList
            items={insight.histogram
              .slice()
              .reverse()
              .map((bucket) => ({
                key: String(bucket.start),
                label: bucketLabel(bucket.start),
                sublabel: bucket.start >= t ? 'matches' : bucket.start + 0.1 > t ? 'spans threshold' : undefined,
                value: bucket.count,
                icon: (
                  <span
                    className={cn(
                      'size-2 shrink-0 rounded-full',
                      bucket.start >= t ? 'bg-chart-emphasis' : 'bg-chart-context',
                    )}
                    aria-hidden="true"
                  />
                ),
              }))}
          />
        )}
      </div>
    </ChartCard>
  )
}

export function LabelDot({ color }: { color: RunLabelInsight['color'] }) {
  return (
    <span
      className={cn('size-2 shrink-0 rounded-full', color ? labelColorClass[color] : 'bg-muted-foreground')}
      aria-hidden="true"
    />
  )
}
