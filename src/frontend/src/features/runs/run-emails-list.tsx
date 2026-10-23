import { ChevronLeft, ChevronRight, Inbox as InboxIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatDateTime, formatNumber, formatSender } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { RunEmailPage, RunEmailSort, RunEmailTab } from './api'
import { RUN_EMAIL_TABS } from './run-email-tabs'
import { LabelDot } from './run-label-insight-card'

const SORTS: { id: RunEmailSort; label: string }[] = [
  { id: 'probability_desc', label: 'Highest confidence' },
  { id: 'probability_asc', label: 'Lowest confidence' },
  { id: 'sent_desc', label: 'Newest first' },
]

const selectClass =
  'h-8 rounded-md border border-input bg-card px-2 text-xs shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/30'

type Props = {
  tab: RunEmailTab
  onTab: (tab: RunEmailTab) => void
  labels: { id: string; name: string }[]
  labelId: string | null
  onLabel: (id: string | null) => void
  sort: RunEmailSort
  onSort: (sort: RunEmailSort) => void
  data: RunEmailPage | undefined
  stale: boolean
  onPage: (page: number) => void
  thresholds: Record<string, number>
}

/** The run's (email, label) results, by tab, with label filter, sort and pagination. */
export function RunEmailsList({ tab, onTab, labels, labelId, onLabel, sort, onSort, data, stale, onPage, thresholds }: Props) {
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1
  const first = data && data.total ? (data.page - 1) * data.page_size + 1 : 0
  const last = data ? Math.min(data.total, data.page * data.page_size) : 0

  return (
    <section className="rounded-xl border bg-card shadow-xs">
      <header className="space-y-3 border-b px-4 py-3 sm:px-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-medium">Emails</h3>
          <span className="text-xs tabular-nums text-muted-foreground">
            {data ? (data.total ? `${formatNumber(first)}–${formatNumber(last)} of ${formatNumber(data.total)}` : 'None') : '…'}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" aria-label="Result" className="flex flex-wrap gap-1 rounded-lg bg-muted p-0.5">
            {RUN_EMAIL_TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => onTab(t.id)}
                className={cn(
                  'rounded-md px-2.5 py-1 text-xs font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring/50',
                  tab === t.id ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="ml-auto flex gap-2">
            {labels.length > 1 && (
              <select
                aria-label="Label"
                className={selectClass}
                value={labelId ?? ''}
                onChange={(e) => onLabel(e.target.value || null)}
              >
                <option value="">All labels</option>
                {labels.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            )}
            <select
              aria-label="Sort"
              className={selectClass}
              value={sort}
              onChange={(e) => onSort(e.target.value as RunEmailSort)}
            >
              {SORTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      {!data ? (
        <p className="px-5 py-10 text-center text-sm text-muted-foreground">Loading…</p>
      ) : data.total === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-muted-foreground">
          {RUN_EMAIL_TABS.find((t) => t.id === tab)?.empty}
        </p>
      ) : (
        <ul className={cn('divide-y transition-opacity', stale && 'opacity-60')}>
          {data.items.map((row) => {
            const threshold = row.result.label_id ? thresholds[row.result.label_id] : undefined
            return (
              <li
                key={`${row.email_id}-${row.result.label_id}`}
                className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:gap-4 sm:px-5"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" title={row.from_address ?? undefined}>
                    {formatSender(row.from_address)}
                  </p>
                  <p className="truncate text-sm">{row.subject || '(no subject)'}</p>
                  {row.snippet && <p className="line-clamp-1 text-xs text-muted-foreground">{row.snippet}</p>}
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <InboxIcon className="size-3" />
                      {row.inbox_name}
                    </span>
                    <time dateTime={row.sent_at}>{formatDateTime(row.sent_at)}</time>
                    {!row.result.from_this_run && <span>Answer reused from an earlier run</span>}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2 sm:flex-col sm:items-end sm:gap-1">
                  <span className="inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-xs">
                    <LabelDot color={row.result.color} />
                    <span className="font-mono">{row.result.label_name}</span>
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    <span className={cn('font-semibold', row.result.matched ? 'text-foreground' : '')}>
                      {Math.round(row.result.probability * 100)}%
                    </span>
                    {threshold !== undefined && ` · needs ${Math.round(threshold * 100)}%`}
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {data && pages > 1 && (
        <footer className="flex items-center justify-between gap-3 border-t px-4 py-2.5 sm:px-5">
          <span className="text-xs tabular-nums text-muted-foreground">
            Page {data.page} of {pages}
          </span>
          <div className="flex gap-1.5">
            <Button variant="outline" size="sm" disabled={data.page <= 1} onClick={() => onPage(data.page - 1)}>
              <ChevronLeft />
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={data.page >= pages} onClick={() => onPage(data.page + 1)}>
              Next
              <ChevronRight />
            </Button>
          </div>
        </footer>
      )}
    </section>
  )
}
