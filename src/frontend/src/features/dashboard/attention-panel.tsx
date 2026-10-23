import { CircleAlert, Filter, History, Inbox as InboxIcon, Scale } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { labelColorClass } from '@/features/labels/colors'
import { formatNumber, formatRelative } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { DashboardAttention } from './api'

type Item = { key: string; icon: ReactNode; text: ReactNode; to: string; tone?: 'warning' | 'destructive' }

function LabelName({ name, color }: { name: string; color: keyof typeof labelColorClass }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-foreground">
      <span className={cn('size-1.5 rounded-full', labelColorClass[color])} aria-hidden="true" />
      {name}
    </span>
  )
}

/** Actionable items, each linking to where it's fixed. Renders nothing when all is well. */
export function AttentionPanel({ data }: { data: DashboardAttention }) {
  const near = data.near_window
  const items: Item[] = [
    ...data.inboxes_with_errors.map((i) => ({
      key: `inbox-${i.inbox_id}`,
      tone: 'destructive' as const,
      icon: <InboxIcon className="size-4" />,
      text: (
        <>
          Inbox <span className="font-medium text-foreground">{i.name}</span> failed its last scan: {i.error}
        </>
      ),
      to: '/connections/inbox',
    })),
    ...data.runs_with_problems.map((r) => ({
      key: `run-${r.run_id}`,
      tone: r.status === 'failed' ? ('destructive' as const) : ('warning' as const),
      icon: <CircleAlert className="size-4" />,
      text: (
        <>
          Run <span className="font-medium text-foreground">{r.name}</span>{' '}
          {r.status === 'failed' ? 'failed' : `finished with ${formatNumber(r.emails_failed)} failed emails`} ·{' '}
          {formatRelative(r.created_at)}
        </>
      ),
      to: `/discovery/runs/${r.run_id}`,
    })),
    ...data.labels_without_condition.map((l) => ({
      key: `nocond-${l.label_id}`,
      tone: 'warning' as const,
      icon: <Filter className="size-4" />,
      text: (
        <>
          <LabelName name={l.name} color={l.color} /> has no filter condition, so runs can't use it
        </>
      ),
      to: `/discovery/labels/${l.label_id}`,
    })),
    ...data.labels_stale.map((l) => ({
      key: `stale-${l.label_id}`,
      tone: 'warning' as const,
      icon: <History className="size-4" />,
      text: (
        <>
          <LabelName name={l.name} color={l.color} />: condition changed since its last run; earlier answers are stale
        </>
      ),
      to: '/discovery/runs',
    })),
    ...data.labels_never_run.map((l) => ({
      key: `never-${l.label_id}`,
      icon: <History className="size-4" />,
      text: (
        <>
          <LabelName name={l.name} color={l.color} /> hasn't been used in a completed run yet
        </>
      ),
      to: '/discovery/runs',
    })),
    ...data.labels_likely_misses.map((l) => ({
      key: `miss-${l.label_id}`,
      icon: <Scale className="size-4" />,
      text: (
        <>
          <LabelName name={l.name} color={l.color} />: {formatNumber(l.count ?? 0)}{' '}
          {l.count === 1 ? 'email' : 'emails'} scored just under the threshold (within {near}) and{' '}
          {l.count === 1 ? "wasn't" : "weren't"} labelled
        </>
      ),
      to: `/discovery/labels/${l.label_id}`,
    })),
    ...data.labels_near_threshold.map((l) => ({
      key: `near-${l.label_id}`,
      icon: <Scale className="size-4" />,
      text: (
        <>
          <LabelName name={l.name} color={l.color} />: {formatNumber(l.count ?? 0)}{' '}
          {l.count === 1 ? 'answer' : 'answers'} within ±{near} of the threshold. Check them to tune it
        </>
      ),
      to: `/discovery/labels/${l.label_id}`,
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
