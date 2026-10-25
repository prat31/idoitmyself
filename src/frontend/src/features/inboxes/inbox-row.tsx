import { AlertCircle } from 'lucide-react'
import { Link } from 'react-router'

import { Figure, ItemRow, MetaDot } from '@/components/layout/item-list'
import { Badge } from '@/components/ui/badge'
import { ScanStatusBadge } from '@/features/scans/scan-status-badge'
import { formatDate, formatDateTime, formatNumber, formatRelative } from '@/lib/format'
import type { Inbox } from './api'
import { providerById } from './providers'

/** One inbox as a list row: name, mailbox type and address; notes; scan state; filters and dates on
 *  the right. */
export function InboxRow({ inbox }: { inbox: Inbox }) {
  const provider = providerById[inbox.provider]
  const Icon = provider.icon
  const scan = inbox.last_scan

  return (
    <ItemRow
      leading={
        <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
          <Icon className="size-[18px]" strokeWidth={1.75} />
        </span>
      }
      title={inbox.name}
      badges={
        <Badge variant="outline" className="text-muted-foreground" title="Mailbox type">
          {provider.label}
        </Badge>
      }
      figures={
        <>
          <Figure
            value={
              <Link to="/automation/filters" className="relative z-10 underline-offset-2 hover:underline">
                {formatNumber(inbox.active_filters)}
              </Link>
            }
            label="Active filters"
            muted={inbox.active_filters === 0}
          />
          <Figure
            value={
              <span className="inline-flex items-center gap-1.5">
                <span className="size-1.5 rounded-full bg-success" aria-hidden="true" />
                {formatDate(inbox.connected_at)}
              </span>
            }
            label="Connected"
          />
        </>
      }
      meta={
        <>
          {inbox.active_filters === 0 ? (
            <span>Not scanned: no active filter covers it</span>
          ) : (
            <span>
              {inbox.scanned_until ? `Scanned up to ${formatDateTime(inbox.scanned_until)}` : 'Not scanned yet'}
            </span>
          )}
          {scan && (
            <>
              <MetaDot />
              <span className="inline-flex items-center gap-1.5">
                Last scan
                <time dateTime={scan.created_at} title={formatDateTime(scan.created_at)}>
                  {formatRelative(scan.created_at)}
                </time>
                <ScanStatusBadge status={scan.status} />
              </span>
            </>
          )}
          {inbox.tags.length > 0 && (
            <span className="flex flex-wrap gap-1.5">
              {inbox.tags.map((tag) => (
                <Badge key={tag.id}>{tag.name}</Badge>
              ))}
            </span>
          )}
        </>
      }
    >
      <p className="truncate text-sm text-muted-foreground">{inbox.email_address}</p>
      {inbox.notes && <p className="line-clamp-2 text-sm text-muted-foreground">{inbox.notes}</p>}
      {scan?.status === 'failed' && scan.error && (
        <p className="flex items-start gap-1.5 text-xs text-destructive" title={scan.error}>
          <AlertCircle className="mt-px size-3.5 shrink-0" />
          <span className="line-clamp-2 break-words">{scan.error}</span>
        </p>
      )}
    </ItemRow>
  )
}
