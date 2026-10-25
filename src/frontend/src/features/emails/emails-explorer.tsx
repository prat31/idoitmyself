import { useEffect, useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Inbox as InboxIcon, Search } from 'lucide-react'

import { ErrorBanner } from '@/components/layout/error-banner'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { LabelDot } from '@/features/labels/label-dot'
import { resolveRange } from '@/features/stats/date-filter'
import { OverviewFilters, type FilterState } from '@/features/stats/overview-filters'
import { formatDate, formatDateTime, formatNumber, formatSender, senderAddress } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useEmails, type EmailRow, type EmailSort } from './api'
import { EmailLink, emailRowClass } from './email-link'

const PAGE_SIZE = 50

const SORTS: { value: EmailSort; label: string }[] = [
  { value: 'sent_desc', label: 'Newest first' },
  { value: 'sent_asc', label: 'Oldest first' },
  { value: 'sender_asc', label: 'Sender A–Z' },
  { value: 'sender_desc', label: 'Sender Z–A' },
  { value: 'subject_asc', label: 'Subject A–Z' },
  { value: 'subject_desc', label: 'Subject Z–A' },
]

type LabelledChoice = 'all' | 'labelled' | 'unlabelled'

/** Waits until `value` has stopped changing for `ms`, so typing doesn't fire a request per key. */
function useDebounced<T>(value: T, ms: number): T {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), ms)
    return () => window.clearTimeout(timer)
  }, [value, ms])
  return settled
}

function Stat({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className={cn('min-w-0', className)}>
      <div className="truncate text-sm font-semibold tabular-nums">{value}</div>
      <div className="truncate text-[11px] text-muted-foreground">{label}</div>
    </div>
  )
}

function EmailItem({ email }: { email: EmailRow }) {
  const address = senderAddress(email.from_address)
  return (
    <li className={cn('flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-start sm:gap-4 sm:px-5', emailRowClass)}>
      <div className="min-w-0 sm:w-56 sm:shrink-0">
        <p className="truncate text-sm font-medium" title={email.from_address ?? undefined}>
          {formatSender(email.from_address)}
        </p>
        {address && <p className="truncate text-xs text-muted-foreground">{address}</p>}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm">
          <EmailLink url={email.open_url}>{email.subject || '(no subject)'}</EmailLink>
        </p>
        {email.snippet && <p className="line-clamp-1 text-xs text-muted-foreground">{email.snippet}</p>}
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <InboxIcon className="size-3" aria-hidden="true" />
            {email.inbox_name}
          </span>
          {email.labels.map((label) => (
            <span
              key={label.label_id}
              className="inline-flex items-center gap-1 rounded-md border px-1.5 py-px text-foreground"
              title={label.filter_name ? `Added by ${label.filter_name}` : 'Its filter was deleted'}
            >
              <LabelDot color={label.color} className="size-1.5" />
              {label.display_name}
            </span>
          ))}
        </div>
      </div>
      <time
        className="shrink-0 text-xs tabular-nums text-muted-foreground sm:pt-0.5 sm:text-right"
        dateTime={email.sent_at}
        title={`Scanned ${formatDateTime(email.scanned_at)}`}
      >
        {formatDateTime(email.sent_at)}
      </time>
    </li>
  )
}

/** A window over the stored emails: the dashboard's filters plus search, labelled/unlabelled and
 *  sorting, stats for everything matching, and a paged list. */
export function EmailsExplorer({
  open,
  onOpenChange,
  initialFilters,
  refetchInterval,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Starts from the dashboard's current filters each time it opens. */
  initialFilters: FilterState
  refetchInterval?: number
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[calc(100svh-2rem)] max-w-6xl flex-col gap-0 overflow-hidden p-0 sm:max-w-6xl">
        {/* Unmounted while closed, so its state starts fresh on every open. */}
        <ExplorerBody initialFilters={initialFilters} refetchInterval={refetchInterval} />
      </DialogContent>
    </Dialog>
  )
}

function ExplorerBody({ initialFilters, refetchInterval }: { initialFilters: FilterState; refetchInterval?: number }) {
  const [filters, setFilters] = useState(initialFilters)
  const [search, setSearch] = useState('')
  const [labelled, setLabelled] = useState<LabelledChoice>('all')
  const [sort, setSort] = useState<EmailSort>('sent_desc')
  const [page, setPage] = useState(1)
  const q = useDebounced(search, 300)
  // A new search starts from the first page.
  const [searchedFor, setSearchedFor] = useState(q)
  if (q !== searchedFor) {
    setSearchedFor(q)
    setPage(1)
  }

  const { start, end } = useMemo(
    () => resolveRange(filters.range, filters.from, filters.to),
    [filters.range, filters.from, filters.to],
  )
  const emails = useEmails(
    {
      start,
      end,
      inboxId: filters.inboxId,
      labelIds: filters.labelIds,
      labelled: labelled === 'all' ? null : labelled === 'labelled',
      q,
      sort,
      page,
      pageSize: PAGE_SIZE,
    },
    refetchInterval,
  )
  const data = emails.data
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1
  const first = data && data.total ? (data.page - 1) * data.page_size + 1 : 0
  const last = data ? Math.min(data.total, data.page * data.page_size) : 0

  return (
    <>
      <DialogHeader className="space-y-1 border-b px-5 pb-4 pt-5">
        <DialogTitle>Emails</DialogTitle>
        <DialogDescription>Every email scans have stored (metadata only, by sent date).</DialogDescription>
      </DialogHeader>

      <div className="space-y-3 border-b px-5 py-3">
        <OverviewFilters
          state={filters}
          onChange={(next) => {
            setFilters((prev) => ({ ...prev, ...next }))
            setPage(1)
          }}
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="relative sm:w-80">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search sender or subject"
              aria-label="Search sender or subject"
              className="pl-8"
            />
          </div>
          <Select
            value={labelled}
            onValueChange={(v) => {
              setLabelled(v as LabelledChoice)
              setPage(1)
            }}
          >
            <SelectTrigger className="sm:w-44" aria-label="Labelled or not">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Labelled or not</SelectItem>
              <SelectItem value="labelled">Labelled only</SelectItem>
              <SelectItem value="unlabelled">Not labelled</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={sort}
            onValueChange={(v) => {
              setSort(v as EmailSort)
              setPage(1)
            }}
          >
            <SelectTrigger className="sm:w-44" aria-label="Sort">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SORTS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {data && (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 border-b px-5 py-3 sm:grid-cols-3 lg:grid-cols-[repeat(5,minmax(0,1fr))_minmax(0,2fr)]">
          <Stat label="Emails" value={formatNumber(data.stats.emails)} />
          <Stat label="Labelled" value={formatNumber(data.stats.labelled)} />
          <Stat label="Not labelled" value={formatNumber(data.stats.unlabelled)} />
          <Stat label="Senders" value={formatNumber(data.stats.senders)} />
          <Stat label="Inboxes" value={formatNumber(data.stats.inboxes)} />
          <Stat
            className="col-span-2 sm:col-span-1"
            label="Sent between"
            value={
              data.stats.first_sent_at && data.stats.last_sent_at
                ? `${formatDate(data.stats.first_sent_at)} – ${formatDate(data.stats.last_sent_at)}`
                : '—'
            }
          />
        </dl>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {emails.isError ? (
          <div className="p-5">
            <ErrorBanner message={`Couldn't load emails: ${emails.error.message}`} onRetry={() => emails.refetch()} />
          </div>
        ) : !data ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-12 rounded-lg" />
            ))}
          </div>
        ) : data.total === 0 ? (
          <p className="px-5 py-16 text-center text-sm text-muted-foreground">No emails match these filters.</p>
        ) : (
          <ul className={cn('divide-y transition-opacity', emails.isPlaceholderData && 'opacity-60')}>
            {data.items.map((email) => (
              <EmailItem key={email.id} email={email} />
            ))}
          </ul>
        )}
      </div>

      {data && data.total > 0 && (
        <footer className="flex items-center justify-between gap-3 border-t px-5 py-2.5">
          <span className="text-xs tabular-nums text-muted-foreground">
            {formatNumber(first)}–{formatNumber(last)} of {formatNumber(data.total)}
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
    </>
  )
}
