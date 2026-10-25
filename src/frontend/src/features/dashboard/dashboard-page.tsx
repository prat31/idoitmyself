import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router'

import { BarList } from '@/components/charts/bar-list'
import { ChartCard, ChartTable } from '@/components/charts/chart-card'
import { ColumnChart } from '@/components/charts/column-chart'
import { StatTile } from '@/components/charts/stat-tile'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { EmailLink, emailRowClass } from '@/features/emails/email-link'
import { LabelDot } from '@/features/labels/label-dot'
import { EmailsExplorer } from '@/features/emails/emails-explorer'
import { useActiveScans, useScans } from '@/features/scans/api'
import { NextScan } from '@/features/scans/next-scan'
import { ScanStatusBadge } from '@/features/scans/scan-status-badge'
import { useOverview } from '@/features/stats/api'
import { DEFAULT_RANGE, RANGE_PRESETS, resolveRange, type RangeId } from '@/features/stats/date-filter'
import { OverviewFilters, type FilterState } from '@/features/stats/overview-filters'
import { bucketTitle, granularityLabel, toColumns } from '@/features/stats/timeline'
import { formatDateTime, formatNumber, formatRelative, formatSender, senderAddress } from '@/lib/format'
import { cn } from '@/lib/utils'
import {
  attentionCount,
  useDashboardAttention,
  useDashboardRecent,
  useDashboardSummary,
  useLiveInterval,
} from './api'
import { AttentionPanel } from './attention-panel'
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

export function DashboardPage() {
  const [params, setParams] = useSearchParams()
  const filters = readFilters(params)
  const { start, end } = useMemo(
    () => resolveRange(filters.range, filters.from, filters.to),
    [filters.range, filters.from, filters.to],
  )
  const update = (next: Partial<FilterState>) => setParams(writeFilters({ ...filters, ...next }), { replace: true })

  // Every section refreshes on its own: quickly while a scan is working, slowly otherwise.
  const live = useLiveInterval()
  const overview = useOverview({ start, end, inboxId: filters.inboxId, labelIds: filters.labelIds }, live)
  const summary = useDashboardSummary(start, end, live)
  const scans = useScans(1, 5)
  const activeScans = useActiveScans()
  const attention = useDashboardAttention(live)
  const recent = useDashboardRecent(5, live)
  const [explorerOpen, setExplorerOpen] = useState(false)

  const isScanning = (activeScans.data?.total ?? 0) > 0
  const activeCount = activeScans.data?.total ?? 0
  const recentMatches = useMemo(() => recent.data?.matches.slice(0, 5) ?? [], [recent.data?.matches])
  const recentScans = useMemo(() => scans.data?.items.slice(0, 5) ?? [], [scans.data?.items])

  const o = overview.data
  const s = summary.data
  const stale = overview.isPlaceholderData || summary.isPlaceholderData

  return (
    <>
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2.5">
            <span>Dashboard</span>
            {isScanning && (
              <Link
                to="/automation/scans"
                className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-0.5 text-xs font-sans font-medium text-foreground shadow-2xs hover:bg-accent transition-colors"
                title={activeCount === 1 ? '1 scan in progress' : `${activeCount} scans in progress`}
              >
                <span className="relative flex size-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-success" />
                </span>
                <span>Scan running</span>
              </Link>
            )}
          </span>
        }
        description={<NextScan />}
      />
      <EmailsExplorer
        open={explorerOpen}
        onOpenChange={setExplorerOpen}
        initialFilters={filters}
        refetchInterval={live}
      />
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
              <StatTile
                label="Emails scanned"
                value={formatNumber(o.totals.emails)}
                hint="Sent in range"
                onClick={() => setExplorerOpen(true)}
              />
              <StatTile
                label="Active filters"
                value={formatNumber(s.active_filters)}
                hint={s.inactive_filters ? `${formatNumber(s.inactive_filters)} inactive` : 'All filters'}
                href="/automation/filters"
              />
              <StatTile
                label="Labelled"
                value={formatNumber(o.totals.labelled_emails)}
                hint={`${percent(o.totals.labelled_emails, o.totals.emails)} of emails`}
                href="/automation/labels"
              />
              <StatTile
                label="Scans completed"
                value={formatNumber(s.scans_completed)}
                hint={s.scans_failed ? `${s.scans_failed} failed` : `${formatNumber(s.emails_labelled)} emails labelled`}
                href="/automation/scans"
              />
            </dl>
          )}

          {/* 3. Needs attention */}
          {attention.data && attentionCount(attention.data) > 0 && (
            <AttentionSection>
              <AttentionPanel data={attention.data} />
            </AttentionSection>
          )}

          {/* 4. Trends */}
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
                      rows={s.label_months.map((l) => [l.display_name, l.this_month, l.last_month])}
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
                            <LabelDot color={l.color} />
                            <Link to={`/automation/labels/${l.label_id}`} className="min-w-0 flex-1 truncate hover:underline">
                              {l.display_name}
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

          {/* 5. Recent activity */}
          <Section title="Recent activity">
            <div className="grid items-start gap-4 lg:grid-cols-2">
              <div className="min-w-0 rounded-xl border bg-card shadow-xs">
                <h3 className="border-b px-4 py-3 text-sm font-medium sm:px-5">Latest labelled emails</h3>
                {!recent.data ? (
                  <Skeleton className="m-4 h-24" />
                ) : recentMatches.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-muted-foreground">Nothing labelled yet.</p>
                ) : (
                  <ul className="divide-y">
                    {recentMatches.map((m) => (
                      <li
                        key={`${m.email_id}-${m.label_id}`}
                        className={cn('flex items-start gap-3 px-4 py-2.5 sm:px-5', emailRowClass)}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium" title={m.from_address ?? undefined}>
                            {formatSender(m.from_address)}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            <EmailLink url={m.open_url}>{m.subject || '(no subject)'}</EmailLink>
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <Link
                            to={`/automation/labels/${m.label_id}`}
                            className="relative z-10 inline-flex items-center gap-1.5 rounded-md border bg-card px-1.5 py-0.5 text-xs hover:bg-accent"
                            title={m.filter_name ? `Added by ${m.filter_name}` : undefined}
                          >
                            <LabelDot color={m.label_color} className="size-1.5" />
                            {m.label_display_name}
                          </Link>
                          <p className="mt-0.5 text-[11px] tabular-nums text-muted-foreground">{formatDateTime(m.sent_at)}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="min-w-0 rounded-xl border bg-card shadow-xs">
                <div className="flex items-center justify-between border-b px-4 py-3 sm:px-5">
                  <h3 className="text-sm font-medium">Latest scans</h3>
                  <Link to="/automation/scans" className="text-xs text-muted-foreground hover:text-foreground">
                    All scans
                  </Link>
                </div>
                {!scans.data ? (
                  <Skeleton className="m-4 h-24" />
                ) : recentScans.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-muted-foreground">No scans yet.</p>
                ) : (
                  <ul className="divide-y">
                    {recentScans.map((scan) => (
                      <li key={scan.id} className="flex items-center gap-3 px-4 py-2.5 sm:px-5">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{scan.inbox_name}</p>
                          <p className="truncate text-xs text-muted-foreground">
                            {formatNumber(scan.emails_matched)} matched of{' '}
                            {formatNumber(scan.emails_processed - scan.emails_skipped)} new ·{' '}
                            {formatRelative(scan.created_at)}
                          </p>
                        </div>
                        <ScanStatusBadge status={scan.status} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </Section>

          {/* 6. Breakdowns */}
          {o && (
            <Section title="Breakdowns" note="in range">
              <div className={cn('grid items-start gap-4 transition-opacity md:grid-cols-2', stale && 'opacity-60')}>
                <ChartCard
                  title="Emails by label"
                  table={<ChartTable columns={['Label', 'Emails']} rows={o.by_label.map((l) => [l.display_name, l.emails])} />}
                >
                  <BarList
                    emptyText="No labels yet"
                    items={o.by_label.map((l) => ({
                      key: l.label_id,
                      label: l.display_name,
                      value: l.emails,
                      href: `/automation/labels/${l.label_id}`,
                      icon: <LabelDot color={l.color} />,
                    }))}
                  />
                </ChartCard>
                <ChartCard
                  title="Emails by filter"
                  table={<ChartTable columns={['Filter', 'Label', 'Emails']} rows={o.by_filter.map((f) => [f.name, f.label_display_name, f.emails])} />}
                >
                  <BarList
                    emptyText="No matches in range"
                    items={o.by_filter.map((f) => ({
                      key: f.filter_id,
                      label: f.name,
                      sublabel: f.label_display_name,
                      value: f.emails,
                      href: `/automation/filters/${f.filter_id}`,
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
        </div>
      </PageBody>
    </>
  )
}

function AttentionSection({ children }: { children: React.ReactNode }) {
  return <Section title="Needs attention">{children}</Section>
}
