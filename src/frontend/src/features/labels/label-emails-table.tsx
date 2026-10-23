import { ChevronLeft, ChevronRight, Inbox as InboxIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { formatDateTime, formatNumber, formatSender } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { EmailPage } from './api'
import { labelColorClass } from './colors'

/** Paginated list of a label's emails: sender, subject + snippet, date, inbox, model confidence. */
export function LabelEmailsTable({
  data,
  stale,
  onPage,
}: {
  data: EmailPage
  stale?: boolean
  onPage: (page: number) => void
}) {
  const pages = Math.max(1, Math.ceil(data.total / data.page_size))
  const first = data.total ? (data.page - 1) * data.page_size + 1 : 0
  const last = Math.min(data.total, data.page * data.page_size)

  return (
    <section className="rounded-xl border bg-card shadow-xs">
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3 sm:px-5">
        <h3 className="text-sm font-medium">Emails</h3>
        <span className="text-xs tabular-nums text-muted-foreground">
          {data.total ? `${formatNumber(first)}–${formatNumber(last)} of ${formatNumber(data.total)}` : 'None yet'}
        </span>
      </header>

      {data.total === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-muted-foreground">
          No emails carry this label yet. Run it from Discovery › Runs.
        </p>
      ) : (
        <ul className={cn('divide-y transition-opacity', stale && 'opacity-60')}>
          {data.items.map((email) => (
            <li key={email.id} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:gap-4 sm:px-5">
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <p className="min-w-0 truncate text-sm font-medium" title={email.from_address ?? undefined}>
                    {formatSender(email.from_address)}
                  </p>
                  <time
                    className="ml-auto shrink-0 text-xs tabular-nums text-muted-foreground sm:hidden"
                    dateTime={email.sent_at}
                  >
                    {formatDateTime(email.sent_at)}
                  </time>
                </div>
                <p className="truncate text-sm">{email.subject || '(no subject)'}</p>
                {email.snippet && <p className="line-clamp-1 text-xs text-muted-foreground">{email.snippet}</p>}
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <InboxIcon className="size-3" />
                    {email.inbox_name}
                  </span>
                  {email.other_labels.map((other) => (
                    <span key={other.label_id} className="inline-flex items-center gap-1 rounded-md border px-1.5 py-px">
                      <span className={cn('size-1.5 rounded-full', labelColorClass[other.color])} aria-hidden="true" />
                      <span className="font-mono">{other.name}</span>
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3 sm:flex-col sm:items-end sm:gap-1">
                <time className="hidden text-xs tabular-nums text-muted-foreground sm:block" dateTime={email.sent_at}>
                  {formatDateTime(email.sent_at)}
                </time>
                <span
                  className="text-xs tabular-nums text-muted-foreground"
                  title={email.run_name ? `Set by run “${email.run_name}”` : undefined}
                >
                  Confidence <span className="font-medium text-foreground">{Math.round(email.probability * 100)}%</span>
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      {pages > 1 && (
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
