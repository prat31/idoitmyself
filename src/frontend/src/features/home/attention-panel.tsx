import { CircleAlert, ExternalLink, Inbox as InboxIcon, KeyRound, ListFilter, Tag } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { formatNumber, formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import { LabelDot } from '@/features/labels/label-dot'
import { InputDialog } from '@/features/processors/input-dialog'
import type { HomeAttention } from './api'

type Item = { key: string; icon: ReactNode; text: ReactNode; to: string; tone?: 'warning' | 'destructive' }

const Strong = ({ children }: { children: ReactNode }) => <span className="font-medium text-foreground">{children}</span>

/** A processor needs something from the user (e.g. a PDF password): asks for it right here, with a
 *  link to the latest waiting email (new tab) to check which one it is. */
function InputItem({ item }: { item: HomeAttention['inputs_needed'][number] }) {
  const emails = item.waiting_runs === 1 ? '1 email waits' : `${formatNumber(item.waiting_runs)} emails wait`
  return (
    <li className="flex flex-col gap-3 px-4 py-3 text-sm text-muted-foreground sm:flex-row sm:items-start sm:px-5">
      <span className="mt-0.5 shrink-0 text-warning">
        <KeyRound className="size-4" />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <p>
          {item.wrong ? "The saved value didn't work: " : 'Needed: '}
          <Strong>{item.prompt}</Strong> · {emails}
        </p>
        {item.open_url ? (
          <a
            href={item.open_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex max-w-full items-center gap-1 text-xs text-foreground underline-offset-2 hover:underline"
          >
            <span className="truncate">{item.email_subject || '(no subject)'}</span>
            <ExternalLink className="size-3 shrink-0" aria-label="Opens in a new tab" />
          </a>
        ) : (
          <p className="truncate text-xs">{item.email_subject || '(no subject)'}</p>
        )}
      </div>
      <div className="shrink-0">
        <InputDialog name={item.name} scope={item.scope} prompt={item.prompt} secret={item.secret} wrong={item.wrong} />
      </div>
    </li>
  )
}

/** Actionable items, each linking to where it's fixed (inputs processors need are asked for in place). Renders
 *  nothing when all is well. */
export function AttentionPanel({ data }: { data: HomeAttention }) {
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
    ...data.filters_skipped_without_ai_key.map((f) => ({
      key: `no-ai-key-${f.filter_id}`,
      tone: 'warning' as const,
      icon: <ListFilter className="size-4" />,
      text: (
        <>
          Filter <Strong>{f.name}</Strong> is skipped by scans: it has AI conditions and OPENROUTER_API_KEY isn't set
        </>
      ),
      to: `/automation/filters/${f.filter_id}`,
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

  if (items.length === 0 && data.inputs_needed.length === 0) return null

  return (
    <ul className="divide-y overflow-hidden rounded-xl border bg-card shadow-xs">
      {data.inputs_needed.map((item) => (
        <InputItem key={`input-${item.name}-${item.scope}`} item={item} />
      ))}
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
