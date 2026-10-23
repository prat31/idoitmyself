import { Link } from 'react-router'

import { formatDate, formatNumber, formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Run } from '@/features/runs/api'
import { RunStatusBadge } from '@/features/runs/run-status-badge'
import type { DashboardStatus } from './api'

/** Runs in progress, and per inbox: last scan, how far back it's scanned, Gmail quota used right now. */
export function LiveStatus({ status, activeRuns }: { status: DashboardStatus; activeRuns: Run[] }) {
  return (
    <div className="grid items-start gap-4 lg:grid-cols-2">
      <div className="min-w-0 rounded-xl border bg-card p-4 shadow-xs sm:p-5">
        <h3 className="mb-3 text-sm font-medium">Runs in progress</h3>
        {activeRuns.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing running.</p>
        ) : (
          <ul className="space-y-3">
            {activeRuns.map((run) => {
              const done = run.emails_processed + run.emails_failed
              return (
                <li key={run.id}>
                  <Link to={`/discovery/runs/${run.id}`} className="block space-y-1.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/50">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="min-w-0 flex-1 truncate font-medium">{run.name}</span>
                      <RunStatusBadge status={run.status} />
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn('h-full rounded-full bg-primary transition-[width] duration-500', !run.emails_found && 'w-1/4 animate-pulse')}
                          style={run.emails_found ? { width: `${Math.min(100, (done / run.emails_found) * 100)}%` } : undefined}
                        />
                      </div>
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                        {run.emails_found ? `${formatNumber(done)} / ${formatNumber(run.emails_found)}` : 'Starting…'}
                      </span>
                    </div>
                  </Link>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="min-w-0 rounded-xl border bg-card p-4 shadow-xs sm:p-5">
        <h3 className="mb-3 text-sm font-medium">Inboxes</h3>
        <ul className="space-y-4">
          {status.inboxes.map((inbox) => {
            const share = Math.min(1, inbox.quota_used / inbox.quota_limit)
            return (
              <li key={inbox.inbox_id} className="space-y-1.5">
                <div className="flex items-baseline gap-2 text-sm">
                  <span className="font-medium">{inbox.name}</span>
                  <span className="truncate text-xs text-muted-foreground">{inbox.email_address}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {inbox.last_scanned_at ? `Last scanned ${formatRelative(inbox.last_scanned_at)}` : 'Never scanned'}
                  {inbox.scanned_since && ` · covered back to ${formatDate(inbox.scanned_since)}`}
                </p>
                <div className="flex items-center gap-3" title="Gmail API quota reserved in the current budget window">
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn('h-full rounded-full transition-[width] duration-500', share >= 0.9 ? 'bg-warning' : 'bg-chart-emphasis')}
                      style={{ width: `${share * 100}%` }}
                    />
                  </div>
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                    Gmail quota {formatNumber(inbox.quota_used)} / {formatNumber(inbox.quota_limit)} per {inbox.quota_window_seconds}s
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
