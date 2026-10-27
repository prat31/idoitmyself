import { useState } from 'react'
import { ArrowDownRight, ArrowUpRight, ChevronLeft, ChevronRight } from 'lucide-react'

import { BarList } from '@/components/charts/bar-list'
import { ChartCard, ChartTable } from '@/components/charts/chart-card'
import { ColumnChart, type ColumnSeries } from '@/components/charts/column-chart'
import { StatTile } from '@/components/charts/stat-tile'
import { ErrorBanner } from '@/components/layout/error-banner'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useRows, useSeries, type Dataset, type QueryScope, type SeriesRow, type Widget } from './api'
import { bucketKeys, bucketLabels, formatAggregate, formatValue, groupLabel } from './values'

// Categorical hues in fixed order (validated); past five, groups fold into "Other".
const SERIES_CLASSES = [
  'bg-chart-series-1',
  'bg-chart-series-2',
  'bg-chart-series-3',
  'bg-chart-series-4',
  'bg-chart-series-5',
]
const OTHER = '__other__'

type WidgetProps = {
  widget: Widget
  dataset: Dataset | undefined
  scope: QueryScope
  /** The same length of time before the range (for stat tiles), or null for all time. */
  previous: QueryScope | null
  /** The range's start, to show empty buckets from there. */
  start: Date | null
}

export function WidgetView(props: WidgetProps) {
  switch (props.widget.type) {
    case 'stat':
      return <StatWidget {...props} />
    case 'timeseries':
    case 'composition':
      return <ColumnsWidget {...props} />
    case 'breakdown':
      return <BreakdownWidget {...props} />
    case 'table':
      return <TableWidget {...props} />
  }
}

function measureField(widget: Widget, dataset: Dataset | undefined) {
  return dataset?.fields.find((f) => f.name === widget.query.measure)
}

function single(rows: SeriesRow[] | undefined): number | null {
  return rows?.[0]?.value ?? (rows ? 0 : null)
}

function StatWidget({ widget, dataset, scope, previous }: WidgetProps) {
  const current = useSeries(widget.query, scope)
  const before = useSeries(widget.query, previous)
  const field = measureField(widget, dataset)
  if (current.isError) return <ErrorBanner message={`${widget.title}: ${current.error.message}`} />
  if (current.isPending) return <Skeleton className="h-[84px] rounded-xl" />
  const value = single(current.data)
  const prior = previous ? single(before.data) : null
  let hint: React.ReactNode = widget.description
  if (prior !== null && value !== null && prior !== 0) {
    const change = ((value - prior) / Math.abs(prior)) * 100
    const Icon = change >= 0 ? ArrowUpRight : ArrowDownRight
    hint = (
      <span className="inline-flex items-center gap-0.5" title={`Previous period: ${formatAggregate(field, prior)}`}>
        <Icon className="size-3" aria-hidden="true" />
        {Math.abs(change).toFixed(0)}% vs previous period
      </span>
    )
  }
  return <StatTile label={widget.title} value={formatAggregate(field, value)} hint={hint} />
}

function ColumnsWidget({ widget, dataset, scope, start }: WidgetProps) {
  const series = useSeries(widget.query, scope)
  const field = measureField(widget, dataset)
  const bucket = widget.query.bucket ?? 'month'
  if (series.isError) return <ErrorBanner message={`${widget.title}: ${series.error.message}`} />
  if (series.isPending) return <Skeleton className="h-64 rounded-xl" />

  const rows = series.data
  const stacked = widget.type === 'composition'
  // Groups by total, biggest first; the top five keep their hue, the rest become "Other".
  const totals = new Map<string, number>()
  for (const row of rows) {
    const group = stacked ? (row.group ?? '') : 'value'
    totals.set(group, (totals.get(group) ?? 0) + (row.value ?? 0))
  }
  const ranked = [...totals.keys()].sort((a, b) => (totals.get(b) ?? 0) - (totals.get(a) ?? 0))
  const kept = ranked.slice(0, ranked.length > SERIES_CLASSES.length ? SERIES_CLASSES.length - 1 : SERIES_CLASSES.length)
  const seriesList: ColumnSeries[] = stacked
    ? [
        ...kept.map((group, i) => ({ key: group, label: groupLabel(group), className: SERIES_CLASSES[i] })),
        ...(ranked.length > kept.length ? [{ key: OTHER, label: 'Other', className: 'bg-chart-context' }] : []),
      ]
    : [{ key: 'value', label: widget.title, className: 'bg-chart-emphasis' }]
  const seriesKey = (group: string) => (!stacked ? 'value' : kept.includes(group) ? group : OTHER)

  const keys = bucketKeys(rows, bucket, start)
  const byBucket = new Map<string, Record<string, number>>(keys.map((k) => [k, {}]))
  for (const row of rows) {
    if (!row.bucket) continue
    const values = byBucket.get(row.bucket.slice(0, 10))
    if (!values) continue
    const k = seriesKey(row.group ?? '')
    values[k] = (values[k] ?? 0) + (row.value ?? 0)
  }
  const data = keys.map((k) => ({ key: k, ...bucketLabels(k, bucket), values: byBucket.get(k) ?? {} }))

  return (
    <ChartCard
      title={widget.title}
      description={widget.description ?? undefined}
      legend={stacked ? seriesList.map((s) => ({ label: s.label, swatchClass: s.className })) : undefined}
      stale={series.isPlaceholderData}
      table={
        <ChartTable
          columns={['Period', ...seriesList.map((s) => s.label)]}
          rows={data.map((d) => [d.title, ...seriesList.map((s) => formatAggregate(field, d.values[s.key] ?? 0))])}
        />
      }
    >
      {rows.length === 0 ? <Empty /> : <ColumnChart data={data} series={seriesList} />}
    </ChartCard>
  )
}

function BreakdownWidget({ widget, dataset, scope }: WidgetProps) {
  const series = useSeries(widget.query, scope)
  const field = measureField(widget, dataset)
  if (series.isError) return <ErrorBanner message={`${widget.title}: ${series.error.message}`} />
  if (series.isPending) return <Skeleton className="h-64 rounded-xl" />
  const rows = series.data.filter((r) => r.value !== null)
  return (
    <ChartCard
      title={widget.title}
      description={widget.description ?? undefined}
      stale={series.isPlaceholderData}
      table={
        <ChartTable
          columns={[dataset?.fields.find((f) => f.name === widget.query.group_by)?.title ?? 'Group', field?.title ?? 'Value']}
          rows={rows.map((r) => [groupLabel(r.group), formatAggregate(field, r.value)])}
        />
      }
    >
      <BarList
        items={rows.map((r) => ({ key: r.group ?? '', label: groupLabel(r.group), value: r.value ?? 0 }))}
        emptyText="Nothing in this range"
      />
    </ChartCard>
  )
}

const PAGE_SIZE = 10

function TableWidget({ widget, dataset, scope }: WidgetProps) {
  const [page, setPage] = useState(1)
  const rows = useRows(widget.query, scope, page, PAGE_SIZE)
  const columns = (widget.query.columns ?? dataset?.fields.map((f) => f.name) ?? [])
    .map((name) => dataset?.fields.find((f) => f.name === name))
    .filter((f) => f !== undefined)
  if (rows.isError) return <ErrorBanner message={`${widget.title}: ${rows.error.message}`} />
  if (rows.isPending) return <Skeleton className="h-48 rounded-xl" />
  const { items, total } = rows.data
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const numeric = (type: string) => type === 'money' || type === 'number'

  return (
    <section className="min-w-0 rounded-xl border bg-card shadow-xs">
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3 sm:px-5">
        <h3 className="text-sm font-medium">{widget.title}</h3>
        <span className="text-xs tabular-nums text-muted-foreground">{total ? formatNumber(total) : 'None yet'}</span>
      </header>
      {total === 0 ? (
        <Empty />
      ) : (
        <div className={cn('overflow-x-auto transition-opacity', rows.isPlaceholderData && 'opacity-60')}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                {columns.map((f) => (
                  <th key={f.name} className={cn('whitespace-nowrap px-3 py-2 font-medium first:pl-4 sm:first:pl-5', numeric(f.type) && 'text-right')}>
                    {f.title}
                  </th>
                ))}
                <th className="px-3 py-2 pr-4 font-medium sm:pr-5">Email</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((record) => (
                <tr key={record.id} className="transition-colors hover:bg-accent/40">
                  {columns.map((f) => (
                    <td
                      key={f.name}
                      className={cn(
                        'whitespace-nowrap px-3 py-2.5 tabular-nums first:pl-4 sm:first:pl-5',
                        numeric(f.type) && 'text-right',
                      )}
                    >
                      {formatValue(f, record.data[f.name])}
                    </td>
                  ))}
                  <td className="max-w-56 px-3 py-2.5 pr-4 sm:pr-5">
                    {record.email?.open_url ? (
                      <a
                        href={record.email.open_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open the email in a new tab"
                        className="block truncate text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                      >
                        {record.email.subject || '(no subject)'}
                      </a>
                    ) : (
                      <span className="block truncate text-muted-foreground">{record.email?.subject ?? '—'}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {pages > 1 && (
        <footer className="flex items-center justify-between gap-3 border-t px-4 py-2.5 sm:px-5">
          <span className="text-xs tabular-nums text-muted-foreground">
            Page {page} of {pages}
          </span>
          <div className="flex gap-1.5">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              <ChevronLeft />
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>
              Next
              <ChevronRight />
            </Button>
          </div>
        </footer>
      )}
    </section>
  )
}

function Empty() {
  return <p className="px-5 py-10 text-center text-sm text-muted-foreground">Nothing in this range yet</p>
}
