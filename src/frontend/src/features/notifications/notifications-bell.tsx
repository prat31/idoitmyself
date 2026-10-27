import { useState } from 'react'
import { Bell, Check, CheckCheck, ExternalLink, MailOpen, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { formatDateTime, formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useDismiss, useMarkAllRead, useMarkRead, useNotifications, type Notification } from './api'

/** The bell: unread count, and a list of notifications. Opening the list marks nothing read: an item is
 *  read once opened (its email, in a new tab) or ticked; "Mark all read" clears the rest. The × dismisses
 *  one (it leaves the list). */
export function NotificationsBell({ align = 'start' }: { align?: 'start' | 'end' }) {
  const [open, setOpen] = useState(false)
  const { data } = useNotifications()
  const markAll = useMarkAllRead()
  const unread = data?.unread ?? 0
  const label = unread ? `Notifications, ${unread} unread` : 'Notifications'

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative size-8 text-muted-foreground" aria-label={label} title={label}>
          <Bell className="size-[18px]" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold tabular-nums text-primary-foreground">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align={align} className="w-[min(24rem,calc(100vw-2rem))] p-0">
        <div className="flex items-center justify-between gap-3 border-b px-4 py-2.5">
          <h2 className="text-sm font-medium">Notifications</h2>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-muted-foreground"
            disabled={!unread || markAll.isPending}
            onClick={() => markAll.mutate()}
          >
            <CheckCheck />
            Mark all read
          </Button>
        </div>
        {!data || data.items.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-muted-foreground">
            Nothing here. Processors notify you, e.g. before a card bill is due or when they can't read an email.
          </p>
        ) : (
          <ul className="max-h-[min(28rem,70vh)] divide-y overflow-y-auto">
            {data.items.map((n) => (
              <NotificationItem key={n.id} notification={n} />
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  )
}

function NotificationItem({ notification: n }: { notification: Notification }) {
  const mark = useMarkRead()
  const dismiss = useDismiss()
  const unread = !n.read_at
  const content = (
    <>
      <span className="flex items-start gap-2">
        <span
          className={cn('mt-1.5 size-1.5 shrink-0 rounded-full', unread ? 'bg-primary' : 'bg-transparent')}
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1">
          <span className={cn('block text-sm', unread ? 'font-medium text-foreground' : 'text-muted-foreground')}>
            {n.title}
            {n.open_url && <ExternalLink className="ml-1 inline size-3 align-[-1px] text-muted-foreground" aria-hidden="true" />}
          </span>
          {n.body && <span className="mt-0.5 block text-xs text-muted-foreground">{n.body}</span>}
          <span className="mt-1 block text-[11px] text-muted-foreground" title={formatDateTime(n.created_at)}>
            {formatRelative(n.created_at)}
            {n.processor_name && ` · ${n.processor_name}`}
          </span>
        </span>
      </span>
    </>
  )
  return (
    <li className={cn('group relative flex items-start gap-1 px-2 py-2.5 transition-colors hover:bg-accent/40', unread && 'bg-accent/20')}>
      {n.open_url ? (
        <a
          href={n.open_url}
          target="_blank"
          rel="noopener noreferrer"
          title="Open the email in a new tab"
          onClick={() => unread && mark.mutate({ id: n.id, read: true })}
          className="min-w-0 flex-1 rounded-md px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
        >
          {content}
        </a>
      ) : (
        <div className="min-w-0 flex-1 px-2">{content}</div>
      )}
      <Button
        variant="ghost"
        size="icon"
        className="size-7 shrink-0 text-muted-foreground opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
        aria-label={unread ? 'Mark as read' : 'Mark as unread'}
        title={unread ? 'Mark as read' : 'Mark as unread'}
        onClick={() => mark.mutate({ id: n.id, read: unread })}
      >
        {unread ? <Check /> : <MailOpen />}
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="size-7 shrink-0 text-muted-foreground opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
        aria-label="Dismiss"
        title="Dismiss"
        disabled={dismiss.isPending}
        onClick={() => dismiss.mutate(n.id)}
      >
        <X />
      </Button>
    </li>
  )
}
