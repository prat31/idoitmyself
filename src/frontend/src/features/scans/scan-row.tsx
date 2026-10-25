import { AlertCircle, ListFilter } from 'lucide-react'

import { Figure, ItemRow } from '@/components/layout/item-list'
import { formatDate, formatDateTime, formatDuration, formatNumber, formatRelative, formatTimeRange } from '@/lib/format'
import { cn } from '@/lib/utils'
import { isActiveScan, scanKindLabel, type Scan } from './api'
import { lastDayOf } from './date-range'
import { ScanStatusBadge } from './scan-status-badge'
import { StopScanDialog } from './stop-scan-dialog'

function coverage(scan: Scan): string {
  if (!scan.window_start || !scan.window_end) return ''
  if (scan.kind === 'adhoc') return `Received ${formatDate(scan.window_start)} – ${formatDate(lastDayOf(scan.window_end))}`
  return `Received ${formatTimeRange(scan.window_start, scan.window_end)}`
}

function duration(scan: Scan): string | null {
  if (!scan.started_at) return null
  const end = scan.finished_at ? new Date(scan.finished_at) : new Date()
  return formatDuration(end.getTime() - new Date(scan.started_at).getTime())
}

/** One scan as a list row: inbox + status, what it covered and timing; key figures on the right. */
export function ScanRow({ scan }: { scan: Scan }) {
  const done = scan.emails_processed + scan.emails_failed
  const progress = scan.emails_found > 0 ? Math.min(100, (done / scan.emails_found) * 100) : 0
  const took = duration(scan)
  const newEmails = scan.emails_processed - scan.emails_skipped

  return (
    <ItemRow
      title={<span title={scan.inbox_email_address}>{scan.inbox_name}</span>}
      badges={
        <>
          <ScanStatusBadge status={scan.status} />
          <span className="rounded-md border px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
            {scanKindLabel[scan.kind]}
          </span>
        </>
      }
      actions={isActiveScan(scan) ? <StopScanDialog scan={scan} /> : undefined}
      figures={
        <>
          <Figure value={formatNumber(scan.emails_found)} label="Found" />
          <Figure value={formatNumber(newEmails)} label="New" />
          <Figure value={formatNumber(scan.emails_matched)} label="Matched" />
          <Figure value={formatNumber(scan.emails_failed)} label="Failed" muted={scan.emails_failed === 0} />
        </>
      }
      meta={
        <>
          {scan.filters.length > 0 && (
            <span className="inline-flex items-center gap-1" title="Filters this scan runs">
              <ListFilter className="size-3" aria-hidden="true" />
              {scan.filters.map((f) => f.name).join(', ')}
            </span>
          )}
          <span className="tabular-nums">+{formatNumber(scan.labels_applied)} labels</span>
          {scan.emails_skipped > 0 && (
            <span className="tabular-nums" title="Already stored by an earlier scan: not fetched or filtered again">
              {formatNumber(scan.emails_skipped)} already scanned
            </span>
          )}
          {scan.retries > 0 && (
            <span className="tabular-nums" title="Emails re-queued with a back-off delay after rate limits or temporary errors">
              {formatNumber(scan.retries)} retries
            </span>
          )}
          {took && <span className="tabular-nums">{took}</span>}
        </>
      }
    >
      <p className="truncate text-sm text-muted-foreground">
        {coverage(scan)} ·{' '}
        <time dateTime={scan.created_at} title={formatDateTime(scan.created_at)}>
          {formatRelative(scan.created_at)}
        </time>
      </p>

      {isActiveScan(scan) && (
        <div className="flex max-w-md items-center gap-3 pt-1">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full rounded-full bg-primary transition-[width] duration-500',
                !scan.emails_found && 'w-1/4 animate-pulse',
              )}
              style={scan.emails_found ? { width: `${progress}%` } : undefined}
            />
          </div>
          <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
            {scan.status === 'queued'
              ? 'Waiting for a worker…'
              : scan.discovered_at
                ? `${formatNumber(done)} / ${formatNumber(scan.emails_found)}`
                : 'Listing emails…'}
          </span>
        </div>
      )}

      {scan.error && (
        <p
          className={cn(
            'flex items-start gap-1.5 text-xs',
            scan.status === 'cancelled' ? 'text-muted-foreground' : 'text-destructive',
          )}
          title={scan.error}
        >
          <AlertCircle className="mt-px size-3.5 shrink-0" />
          <span className="line-clamp-2 break-words">{scan.error}</span>
        </p>
      )}
    </ItemRow>
  )
}
