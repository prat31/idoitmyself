import { Link } from 'react-router'

import { providerById } from '@/features/inboxes/providers'
import { scanKindLabel } from '@/features/scans/api'
import { intervalTitle } from '@/features/scans/interval'
import { ScanStatusBadge } from '@/features/scans/scan-status-badge'
import { formatNumber, formatRelative, formatTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { HomeStatus } from './api'

type InboxStatus = HomeStatus['inboxes'][number]

function ScanProgress({ scan }: { scan: NonNullable<InboxStatus['active_scan']> }) {
  const done = scan.emails_processed + scan.emails_failed
  return (
    <div className="flex items-center gap-3">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full bg-primary transition-[width] duration-500', !scan.emails_found && 'w-1/4 animate-pulse')}
          style={scan.emails_found ? { width: `${Math.min(100, (done / scan.emails_found) * 100)}%` } : undefined}
        />
      </div>
      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
        {scan.discovered_at ? `${formatNumber(done)} / ${formatNumber(scan.emails_found)}` : 'Listing…'}
      </span>
    </div>
  )
}

/** Scans in progress, and per inbox: how far it is scanned, last completed scan, quota used right now. */
export function LiveStatus({ status }: { status: HomeStatus }) {
  const active = status.inboxes.filter((i) => i.active_scan)
  return (
    <div className="grid items-start gap-4 lg:grid-cols-2">
      <div className="min-w-0 rounded-xl border bg-card p-4 shadow-xs sm:p-5">
        <div className="mb-3 flex items-baseline justify-between gap-2">
          <h3 className="text-sm font-medium">Scans in progress</h3>
          <span className="text-xs text-muted-foreground">{intervalTitle(status.scan_interval_minutes)}</span>
        </div>
        {active.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing scanning right now.</p>
        ) : (
          <ul className="space-y-3">
            {active.map(({ inbox_id, name, active_scan: scan }) => (
              <li key={inbox_id}>
                <Link
                  to="/automation/scans"
                  className="block space-y-1.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span className="min-w-0 flex-1 truncate font-medium">{name}</span>
                    <span className="text-xs text-muted-foreground">
                      {scanKindLabel[scan!.kind]}
                    </span>
                    <ScanStatusBadge status={scan!.status} />
                  </div>
                  <ScanProgress scan={scan!} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="min-w-0 rounded-xl border bg-card p-4 shadow-xs sm:p-5">
        <h3 className="mb-3 text-sm font-medium">Inboxes</h3>
        {status.inboxes.length === 0 ? (
          <p className="text-sm text-muted-foreground">No inboxes connected.</p>
        ) : (
          <ul className="space-y-4">
            {status.inboxes.map((inbox) => {
              const share = Math.min(1, inbox.quota_used / inbox.quota_limit)
              const provider = providerById[inbox.provider as keyof typeof providerById]?.label ?? inbox.provider
              return (
                <li key={inbox.inbox_id} className="space-y-1.5">
                  <div className="flex items-baseline gap-2 text-sm">
                    <span className="font-medium">{inbox.name}</span>
                    <span className="truncate text-xs text-muted-foreground">{inbox.email_address}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {inbox.last_completed_scan_at ? `Last scanned ${formatRelative(inbox.last_completed_scan_at)}` : 'Never scanned'}
                    {inbox.scanned_until && ` · up to ${formatTime(inbox.scanned_until)}`}
                  </p>
                  <div className="flex items-center gap-3" title={`${provider} API quota reserved in the current budget window`}>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn('h-full rounded-full transition-[width] duration-500', share >= 0.9 ? 'bg-warning' : 'bg-chart-emphasis')}
                        style={{ width: `${share * 100}%` }}
                      />
                    </div>
                    <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                      {provider} quota {formatNumber(inbox.quota_used)} / {formatNumber(inbox.quota_limit)} per{' '}
                      {inbox.quota_window_seconds}s
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
