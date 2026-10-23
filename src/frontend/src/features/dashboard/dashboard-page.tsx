import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router'

import { BarList } from '@/components/charts/bar-list'
import { ChartCard, ChartTable } from '@/components/charts/chart-card'
import { ColumnChart } from '@/components/charts/column-chart'
import { StatTile } from '@/components/charts/stat-tile'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { labelColorClass } from '@/features/labels/colors'
import { useRuns } from '@/features/runs/api'
import { RunStatusBadge } from '@/features/runs/run-status-badge'
import { useOverview } from '@/features/stats/api'
import { DEFAULT_RANGE, RANGE_PRESETS, resolveRange, type RangeId } from '@/features/stats/date-filter'
import { OverviewFilters, type FilterState } from '@/features/stats/overview-filters'
import { bucketTitle, granularityLabel, toColumns } from '@/features/stats/timeline'
import { formatCost, formatDateTime, formatNumber, formatRelative, formatSender, senderAddress } from '@/lib/format'
import { cn } from '@/lib/utils'
import {
  useDashboardAttention,
  useDashboardCoverage,
  useDashboardRecent,
  useDashboardStatus,
  useDashboardSummary,
} from './api'
import { AttentionPanel } from './attention-panel'
import { CoverageStrip } from './coverage-strip'
import { LiveStatus } from './live-status'
import { Section } from './section'

const RANGE_IDS = new Set<string>([...RANGE_PRESETS.map((p) => p.id), 'custom'])

function readFilters(params: URLSearchParams): FilterState {
  const range = params.get('range') ?? DEFAULT_RANGE
  return {
    range: (RANGE_IDS.has(range) ? range : DEFAULT_RANGE) as RangeId,
    from: params.get('from'),
    to: params.get('to'),
    inboxId: params.get('inbox'),
    labelIds: params.getAll('label'),
  }
}

function writeFilters(state: FilterState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.range !== DEFAULT_RANGE) params.set('range', state.range)
  if (state.range === 'custom' && state.from && state.to) {
    params.set('from', state.from)
    params.set('to', state.to)
  }
  if (state.inboxId) params.set('inbox', state.inboxId)
  state.labelIds.forEach((id) => params.append('label', id))
  return params
}

const percent = (part: number, whole: number) => (whole ? `${Math.round((part / whole) * 100)}%` : '—')

const dot = (color: keyof typeof labelColorClass) => (
  <span className={cn('size-2 shrink-0 rounded-full', labelColorClass[color])} aria-hidden="true" />
)

export function DashboardPage() {
  const [params, setParams] = useSearchParams()
  const filters = readFilters(params)
  const { start, end } = useMemo(
    () => resolveRange(filters.range, filters.from, filters.to),
    [filters.range, filters.from, filters.to],
  )
  const update = (next: Partial<FilterState>) => setParams(writeFilters({ ...filters, ...next }), { replace: true })

  const overview = useOverview({ start, end, inboxId: filters.inboxId, labelIds: filters.labelIds })
  const summary = useDashboardSummary(start, end)
  const runs = useRuns()
  const activeRuns = (runs.data ?? []).filter((r) => r.status === 'queued' || r.status === 'running')
  const attention = useDashboardAttention()
  const status = useDashboardStatus(activeRuns.length > 0)
  const coverage = useDashboardCoverage()
  const recent = useDashboardRecent()

  const o = overview.data
  const s = summary.data
  const stale = overview.isPlaceholderData || summary.isPlaceholderData

  return (
    <>
      <PageHeader title="Dashboard" description="Everything at a glance. Counts cover emails scanned by runs." />
      <PageBody>
        <div className="space-y-8">
          {/* 1. Filters scope the sections marked "in range" */}
          <OverviewFilters state={filters} onChange={update} />

          {/* 2. Headline */}
          {overview.isError ? (
            <ErrorBanner message={`Couldn't load stats: ${overview.error.message}`} onRetry={() => overview.refetch()} />
          ) : !o || !s ? (
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-[84px] rounded-xl" />
              ))}
            </div>
          ) : (
            <dl className={cn('grid grid-cols-2 gap-3 transition-opacity lg:grid-cols-4', stale && 'opacity-60')}>
              <StatTile label="Emails scanned" value={formatNumber(o.totals.emails)} hint="Sent in range" />
              <StatTile
                label="Labelled"
                value={formatNumber(o.totals.labelled_emails)}
                hint={`${percent(o.totals.labelled_emails, o.totals.emails)} of emails`}
              />
              <StatTile
                label="Runs completed"
                value={formatNumber(s.runs_completed)}
                hint={s.runs_failed ? `${s.runs_failed} failed` : 'Finished in range'}
              />
              <StatTile
                label="Model spend"
                value={formatCost(Number(s.cost_usd))}
                hint={Number(s.estimated_saved_usd) > 0 ? `~${formatCost(Number(s.estimated_saved_usd))} saved by skipping` : 'Finished in range'}
              />
            </dl>
          )}

          {/* 3. Needs attention */}
          {attention.data && (
            <AttentionSection>
              <AttentionPanel data={attention.data} />
            </AttentionSection>
          )}

          {/* 4. Live status */}
          <Section title="Live status">
            {status.data ? (
              <LiveStatus status={status.data} activeRuns={activeRuns} />
            ) : (
              <Skeleton className="h-32 rounded-xl" />
            )}
          </Section>

          {/* 5. Trends */}
          {o && s && (
            <Section title="Trends" note="in range">
              <div className={cn('grid items-start gap-4 transition-opacity xl:grid-cols-3', stale && 'opacity-60')}>
                <ChartCard
                  className="xl:col-span-2"
                  title="Emails over time"
                  description={`${granularityLabel[o.granularity]} · by sent date`}
                  legend={[
                    { label: 'Labelled', swatchClass: 'bg-chart-emphasis' },
                    { label: 'Unlabelled', swatchClass: 'bg-chart-context' },
                  ]}
                  table={
                    <ChartTable
                      columns={['Period', 'Emails', 'Labelled']}
                      rows={o.timeline.map((b) => [bucketTitle(b, o.granularity), b.emails, b.labelled])}
                    />
                  }
                >
                  <ColumnChart
                    series={[
                      { key: 'labelled', label: 'Labelled', className: 'bg-chart-emphasis' },
                      { key: 'unlabelled', label: 'Unlabelled', className: 'bg-chart-context' },
                    ]}
                    data={toColumns(o.timeline, o.granularity, (b) => ({ labelled: b.labelled, unlabelled: b.emails - b.labelled }))}
                  />
                </ChartCard>
                <ChartCard
                  title="This month vs last"
                  description="Labelled emails by sent month · all inboxes"
                  table={
                    <ChartTable
                      columns={['Label', 'This month', 'Last month']}
                      rows={s.label_months.map((l) => [l.name, l.this_month, l.last_month])}
                    />
                  }
                >
                  {s.label_months.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No labels yet.</p>
                  ) : (
                    <ul className="space-y-3">
                      {s.label_months.map((l) => {
                        const delta = l.this_month - l.last_month
                        return (
                          <li key={l.label_id} className="flex items-center gap-2 text-sm">
                            {dot(l.color)}
                            <Link to={`/discovery/labels/${l.label_id}`} className="min-w-0 flex-1 truncate font-mono hover:underline">
                              {l.name}
                            </Link>
                            <span className="font-semibold tabular-nums">{formatNumber(l.this_month)}</span>
                            <span className="w-24 text-right text-xs tabular-nums text-muted-foreground">
                              {delta === 0 ? 'same as last' : `${delta > 0 ? '+' : '−'}${Math.abs(delta)} vs ${l.last_month}`}
                            </span>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </ChartCard>
              </div>
            </Section>
          )}

          {/* 6. Breakdowns */}
          {o && (
            <Section title="Breakdowns" note="in range">
              <div className={cn('grid items-start gap-4 transition-opacity lg:grid-cols-3', stale && 'opacity-60')}>
                <ChartCard
                  title="Emails by label"
                  table={<ChartTable columns={['Label', 'Emails']} rows={o.by_label.map((l) => [l.name, l.emails])} />}
                >
                  <BarList
                    emptyText="No labels yet"
                    items={o.by_label.map((l) => ({
                      key: l.label_id,
                      label: l.name,
                      value: l.emails,
                      mono: true,
                      href: `/discovery/labels/${l.label_id}`,
                      icon: dot(l.color),
                    }))}
                  />
                </ChartCard>
                <ChartCard
                  title="Top senders"
                  table={<ChartTable columns={['Sender', 'Emails']} rows={o.top_senders.map((x) => [x.sender, x.emails])} />}
                >
                  <BarList
                    emptyText="No emails in range"
                    items={o.top_senders.map((x) => ({
                      key: x.sender,
                      label: formatSender(x.sender),
                      sublabel: senderAddress(x.sender) ?? undefined,
                      title: x.sender,
                      value: x.emails,
                    }))}
                  />
                </ChartCard>
                <ChartCard
                  title="Emails by inbox"
                  table={<ChartTable columns={['Inbox', 'Emails']} rows={o.by_inbox.map((i) => [i.name, i.emails])} />}
                >
                  <BarList
                    emptyText="No emails in range"
                    items={o.by_inbox.map((i) => ({ key: i.inbox_id, label: i.name, sublabel: i.email_address, value: i.emails }))}
                  />
                </ChartCard>
              </div>
            </Section>
          )}

          {/* 7. Coverage */}
          <Section title="Coverage" note="date ranges already classified per label, current condition, all inboxes">
            {coverage.data ? <CoverageStrip data={coverage.data} /> : <Skeleton className="h-24 rounded-xl" />}
          </Section>

          {/* 8. Recent activity */}
          <Section title="Recent activity">
            <div className="grid items-start gap-4 lg:grid-cols-2">
              <div className="min-w-0 rounded-xl border bg-card shadow-xs">
                <h3 className="border-b px-4 py-3 text-sm font-medium sm:px-5">Latest labelled emails</h3>
                {!recent.data ? (
                  <Skeleton className="m-4 h-24" />
                ) : recent.data.matches.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-muted-foreground">Nothing labelled yet.</p>
                ) : (
                  <ul className="divide-y">
                    {recent.data.matches.map((m) => (
                      <li key={`${m.email_id}-${m.label_id}`} className="flex items-start gap-3 px-4 py-2.5 sm:px-5">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium" title={m.from_address ?? undefined}>
                            {formatSender(m.from_address)}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">{m.subject || '(no subject)'}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <Link
                            to={`/discovery/labels/${m.label_id}`}
                            className="inline-flex items-center gap-1.5 rounded-md border px-1.5 py-0.5 text-xs hover:bg-accent"
                          >
                            {dot(m.color)}
                            <span className="font-mono">{m.label_name}</span>
                          </Link>
                          <p className="mt-0.5 text-[11px] tabular-nums text-muted-foreground">
                            {Math.round(m.probability * 100)}% · {formatDateTime(m.sent_at)}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="min-w-0 rounded-xl border bg-card shadow-xs">
                <div className="flex items-center justify-between border-b px-4 py-3 sm:px-5">
                  <h3 className="text-sm font-medium">Latest runs</h3>
                  <Link to="/discovery/runs" className="text-xs text-muted-foreground hover:text-foreground">
                    All runs
                  </Link>
                </div>
                {!runs.data ? (
                  <Skeleton className="m-4 h-24" />
                ) : runs.data.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-muted-foreground">No runs yet.</p>
                ) : (
                  <ul className="divide-y">
                    {runs.data.slice(0, 5).map((run) => (
                      <li key={run.id}>
                        <Link
                          to={`/discovery/runs/${run.id}`}
                          className="flex items-center gap-3 px-4 py-2.5 outline-none transition-colors hover:bg-accent/40 focus-visible:bg-accent/40 sm:px-5"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">{run.name}</p>
                            <p className="truncate text-xs text-muted-foreground">
                              {formatNumber(run.emails_matched)} matched of {formatNumber(run.emails_found)} ·{' '}
                              {formatRelative(run.created_at)}
                            </p>
                          </div>
                          <RunStatusBadge status={run.status} />
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </Section>

          {/* 9. Spend */}
          {s && (
            <Section title="Model spend" note="in range, by run finish time">
              <div className={cn('grid items-start gap-4 transition-opacity xl:grid-cols-3', stale && 'opacity-60')}>
                <ChartCard
                  className="xl:col-span-2"
                  title="Spend over time"
                  description={`${granularityLabel[s.spend_granularity]} · in US cents`}
                  table={
                    <ChartTable
                      columns={['Period', 'Cost (USD)', 'Emails to model']}
                      rows={s.spend.map((b) => [
                        bucketTitle({ start: b.start, emails: 0, labelled: 0 }, s.spend_granularity),
                        Number(b.cost_usd).toFixed(4),
                        b.emails,
                      ])}
                    />
                  }
                >
                  <ColumnChart
                    series={[{ key: 'cents', label: '¢ spent', className: 'bg-chart-emphasis' }]}
                    data={toColumns(
                      s.spend.map((b) => ({ start: b.start, emails: 0, labelled: 0 })),
                      s.spend_granularity,
                      (b) => ({ cents: Math.round(Number(s.spend.find((x) => x.start === b.start)?.cost_usd ?? 0) * 100) }),
                    )}
                  />
                </ChartCard>
                <dl className="grid grid-cols-2 gap-3 xl:grid-cols-1">
                  <StatTile
                    label="Per run"
                    value={s.runs_completed ? formatCost(Number(s.cost_usd) / s.runs_completed) : '—'}
                    hint={`${formatNumber(s.runs_completed)} completed`}
                  />
                  <StatTile
                    label="Per email"
                    value={s.emails_sent_to_model ? formatCost(Number(s.cost_usd) / s.emails_sent_to_model) : '—'}
                    hint={`${formatNumber(s.emails_sent_to_model)} sent to model`}
                  />
                </dl>
              </div>
            </Section>
          )}
        </div>
      </PageBody>
    </>
  )
}

function AttentionSection({ children }: { children: React.ReactNode }) {
  return <Section title="Needs attention">{children}</Section>
}
