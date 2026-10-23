import { AlertCircle, Inbox as InboxIcon } from 'lucide-react'
import { Link } from 'react-router'

import { Figure, ItemRow } from '@/components/layout/item-list'
import { formatCost, formatDate, formatDateTime, formatDuration, formatNumber, formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Run } from './api'
import { RunStatusBadge } from './run-status-badge'

function windowLabel(run: Run): string {
  // window_end is exclusive (midnight after the last day); show the inclusive last day.
  const first = formatDate(run.window_start)
  const last = formatDate(new Date(new Date(run.window_end).getTime() - 1))
  return first === last ? first : `${first} – ${last}`
}

function duration(run: Run): string | null {
  if (!run.started_at) return null
  const end = run.finished_at ? new Date(run.finished_at) : new Date()
  return formatDuration(end.getTime() - new Date(run.started_at).getTime())
}

/** One run as a list row: name + status, window and timing; key figures on the right. */
export function RunRow({ run }: { run: Run }) {
  const done = run.emails_processed + run.emails_failed
  const progress = run.emails_found > 0 ? Math.min(100, (done / run.emails_found) * 100) : 0
  const active = run.status === 'queued' || run.status === 'running'
  const took = duration(run)

  return (
    <ItemRow
      title={
        // Stretched link: the whole row opens the run's detail page.
        <Link
          to={`/discovery/runs/${run.id}`}
          title={run.name}
          className="outline-none after:absolute after:inset-0 focus-visible:underline"
        >
          {run.name}
        </Link>
      }
      badges={<RunStatusBadge status={run.status} />}
      figures={
        <>
          <Figure value={formatNumber(run.emails_found)} label="Found" />
          <Figure value={formatNumber(run.emails_processed)} label="Classified" />
          <Figure value={formatNumber(run.emails_matched)} label="Matched" />
          <Figure value={formatNumber(run.emails_failed)} label="Failed" muted={run.emails_failed === 0} />
        </>
      }
      meta={
        <>
          <span className="flex flex-wrap gap-1.5">
            {run.labels.map((label) => (
              <span
                key={label.label_name}
                className="inline-flex items-center gap-1.5 rounded-md border px-1.5 py-px"
                title={`${label.filter_condition}\nMatch ≥ ${label.match_threshold.toFixed(2)}`}
              >
                <span className={cn('font-mono text-foreground', !label.label_id && 'line-through opacity-60')}>
                  {label.label_name}
                </span>
                <span className="tabular-nums">{formatNumber(label.matched)}</span>
              </span>
            ))}
          </span>
          <span
            className={cn('flex items-center gap-1', run.inboxes.some((i) => i.error) && 'text-destructive')}
            title={run.inboxes.map((i) => `${i.inbox_name} · ${i.email_address}${i.error ? ` — ${i.error}` : ''}`).join('\n')}
          >
            <InboxIcon className="size-3" />
            {run.inboxes.length === 1 ? run.inboxes[0].inbox_name : `${run.inboxes.length} inboxes`}
          </span>
          <span className="tabular-nums" title="Labels applied / removed">
            +{formatNumber(run.labels_applied)} / −{formatNumber(run.labels_removed)} labels
          </span>
          {run.emails_skipped > 0 && (
            <span className="tabular-nums" title="Already answered for every label: no fetch and no model call">
              {formatNumber(run.emails_skipped)} skipped
            </span>
          )}
          {run.retries > 0 && (
            <span className="tabular-nums" title="Emails re-queued with a back-off delay after rate limits or temporary errors">
              {formatNumber(run.retries)} retries
            </span>
          )}
          <span className="tabular-nums" title={`Model ${run.model}`}>
            {formatCost(Number(run.cost_usd))}
            {took && ` · ${took}`}
          </span>
        </>
      }
    >
      <p className="truncate text-sm text-muted-foreground">
        {windowLabel(run)}
        {run.reclassify && ' · Re-classify'} ·{' '}
        <time dateTime={run.created_at} title={formatDateTime(run.created_at)}>
          {formatRelative(run.created_at)}
        </time>
      </p>

      {active && (
        <div className="flex max-w-md items-center gap-3 pt-1">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full rounded-full bg-primary transition-[width] duration-500',
                !run.emails_found && 'w-1/4 animate-pulse',
              )}
              style={run.emails_found ? { width: `${progress}%` } : undefined}
            />
          </div>
          <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
            {run.status === 'queued'
              ? 'Waiting for a worker…'
              : run.emails_found
                ? `${formatNumber(done)} / ${formatNumber(run.emails_found)}`
                : 'Fetching emails…'}
          </span>
        </div>
      )}

      {run.error && (
        <p className="flex items-start gap-1.5 text-xs text-destructive" title={run.error}>
          <AlertCircle className="mt-px size-3.5 shrink-0" />
          <span className="line-clamp-2 break-words">{run.error}</span>
        </p>
      )}
    </ItemRow>
  )
}
