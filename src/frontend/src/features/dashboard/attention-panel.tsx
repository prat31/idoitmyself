import { CircleAlert, Inbox as InboxIcon, ListFilter, Tag } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { formatNumber, formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import { LabelDot } from '@/features/labels/label-dot'
import type { DashboardAttention } from './api'

type Item = { key: string; icon: ReactNode; text: ReactNode; to: string; tone?: 'warning' | 'destructive' }

const Strong = ({ children }: { children: ReactNode }) => <span className="font-medium text-foreground">{children}</span>

/** Actionable items, each linking to where it's fixed. Renders nothing when all is well. */
export function AttentionPanel({ data }: { data: DashboardAttention }) {
  const items: Item[] = [
    ...data.inboxes_with_errors.map((i) => ({
      key: `inbox-${i.inbox_id}`,
      tone: 'destructive' as const,
      icon: <InboxIcon className="size-4" />,
      text: (
        <>
          Inbox <Strong>{i.name}</Strong> failed its last scan: {i.error}
        </>
      ),
      to: '/connections/inbox',
    })),
    ...data.scans_with_problems.map((s) => ({
      key: `scan-${s.scan_id}`,
      tone: s.status === 'failed' ? ('destructive' as const) : ('warning' as const),
      icon: <CircleAlert className="size-4" />,
      text: (
        <>
          A scan of <Strong>{s.inbox_name}</Strong>{' '}
          {s.status === 'failed' ? 'failed' : `finished with ${formatNumber(s.emails_failed)} failed emails`} ·{' '}
          {formatRelative(s.created_at)}
        </>
      ),
      to: '/automation/scans',
    })),
    ...data.inboxes_without_filters.map((i) => ({
      key: `unfiltered-${i.inbox_id}`,
      tone: 'warning' as const,
      icon: <InboxIcon className="size-4" />,
      text: (
        <>
          <Strong>{i.name}</Strong> isn't scanned: no active filter covers it
        </>
      ),
      to: '/automation/filters',
    })),
    ...data.filters_never_matched.map((f) => ({
      key: `never-${f.filter_id}`,
      icon: <ListFilter className="size-4" />,
      text: (
        <>
          Filter <Strong>{f.name}</Strong> hasn't added <Strong>{f.label_display_name}</Strong> to any email yet
        </>
      ),
      to: `/automation/filters/${f.filter_id}`,
    })),
    ...data.labels_without_active_filter.map((l) => ({
      key: `label-${l.label_id}`,
      icon: <Tag className="size-4" />,
      text: (
        <>
          No active filter adds{' '}
          <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
            <LabelDot color={l.color} />
            {l.display_name}
          </span>
        </>
      ),
      to: `/automation/labels/${l.label_id}`,
    })),
  ]

  if (items.length === 0) return null

  return (
    <ul className="divide-y overflow-hidden rounded-xl border bg-card shadow-xs">
      {items.map((item) => (
        <li key={item.key}>
          <Link
            to={item.to}
            className="flex items-start gap-3 px-4 py-3 text-sm text-muted-foreground transition-colors outline-none hover:bg-accent/40 focus-visible:bg-accent/40 sm:px-5"
          >
            <span
              className={cn(
                'mt-0.5 shrink-0',
                item.tone === 'destructive' && 'text-destructive',
                item.tone === 'warning' && 'text-warning',
              )}
            >
              {item.icon}
            </span>
            <span className="min-w-0">{item.text}</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
