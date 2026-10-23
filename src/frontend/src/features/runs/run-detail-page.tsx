import { AlertCircle, ArrowLeft, Info } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router'

import { BarList } from '@/components/charts/bar-list'
import { ChartCard, ChartTable } from '@/components/charts/chart-card'
import { ColumnChart } from '@/components/charts/column-chart'
import { StatTile } from '@/components/charts/stat-tile'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { Skeleton } from '@/components/ui/skeleton'
import { bucketTitle, granularityLabel, toColumns } from '@/features/stats/timeline'
import { formatCost, formatDate, formatDateTime, formatDuration, formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useRun, useRunEmails, useRunInsights, type Run, type RunEmailSort, type RunEmailTab } from './api'
import { RUN_EMAIL_TABS } from './run-email-tabs'
import { RunEmailsList } from './run-emails-list'
import { RunLabelInsightCard } from './run-label-insight-card'
import { RunStatusBadge } from './run-status-badge'

const PAGE_SIZE = 25
const TAB_IDS = new Set<string>(RUN_EMAIL_TABS.map((t) => t.id))
const SORT_IDS = new Set<string>(['probability_desc', 'probability_asc', 'sent_desc'])

function windowLabel(run: Run): string {
  const first = formatDate(run.window_start)
  const last = formatDate(new Date(new Date(run.window_end).getTime() - 1))
  return first === last ? first : `${first} – ${last}`
}

function durationMs(run: Run): number | null {
  if (!run.started_at) return null
  const end = run.finished_at ? new Date(run.finished_at) : new Date()
  return end.getTime() - new Date(run.started_at).getTime()
}

export function RunDetailPage() {
  const { runId = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const tab = (TAB_IDS.has(params.get('tab') ?? '') ? params.get('tab') : 'matched') as RunEmailTab
  const sort = (SORT_IDS.has(params.get('sort') ?? '') ? params.get('sort') : 'probability_desc') as RunEmailSort
  const labelId = params.get('label')
  const page = Math.max(1, Number(params.get('page')) || 1)

  const run = useRun(runId)
  const live = run.data?.status === 'queued' || run.data?.status === 'running'
  const insights = useRunInsights(runId, live)
  const emails = useRunEmails(runId, { tab, labelId, sort, page, pageSize: PAGE_SIZE })

  const update = (next: Record<string, string | null>) => {
    const merged = new URLSearchParams(params)
    for (const [key, value] of Object.entries(next)) {
      if (value === null) merged.delete(key)
      else merged.set(key, value)
    }
    if (!('page' in next)) merged.delete('page')
    setParams(merged, { replace: true })
  }

  const backLink = (
    <Link
      to="/discovery/runs"
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" />
      Runs
    </Link>
  )

  if (run.isError) {
    return (
      <PageBody>
        <div className="space-y-4">
          {backLink}
          <ErrorBanner message={`Couldn't load the run: ${run.error.message}`} onRetry={() => run.refetch()} />
        </div>
      </PageBody>
    )
  }

  const r = run.data
  const ms = r ? durationMs(r) : null
  const sentToModel = r ? r.emails_processed - r.emails_skipped : 0
  const perMinute = r && ms && ms > 0 ? (r.emails_processed + r.emails_failed) / (ms / 60_000) : null

  return (
    <>
      <header className="space-y-4 border-b px-4 pb-5 pt-6 md:px-10 md:pb-6 md:pt-8">
        {backLink}
        {!r ? (
          <Skeleton className="h-9 w-72" />
        ) : (
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-serif text-2xl font-semibold tracking-tight md:text-3xl">{r.name}</h1>
              <RunStatusBadge status={r.status} />
            </div>
            <p className="text-sm text-muted-foreground">
              {windowLabel(r)}
              {r.reclassify && ' · Re-classify'} · created {formatDateTime(r.created_at)}
              {r.finished_at && ` · finished ${formatDateTime(r.finished_at)}`} · model{' '}
              <span className="font-mono">{r.model}</span>
            </p>
            {r.error && (
              <p className="flex items-start gap-2 pt-1 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span className="break-words">{r.error}</span>
              </p>
            )}
          </div>
        )}
      </header>

      <PageBody>
        {!r ? (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {Array.from({ length: 8 }, (_, i) => (
              <Skeleton key={i} className="h-[84px] rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              <StatTile label="Emails found" value={formatNumber(r.emails_found)} hint="In the date range" />
              <StatTile
                label="Skipped"
                value={formatNumber(r.emails_skipped)}
                hint="Answers reused"
              />
              <StatTile label="Sent to model" value={formatNumber(sentToModel)} hint="Classified now" />
              <StatTile
                label="Matched"
                value={formatNumber(r.emails_matched)}
                hint={`+${formatNumber(r.labels_applied)} / −${formatNumber(r.labels_removed)} labels`}
              />
              <StatTile
                label="Failed"
                value={formatNumber(r.emails_failed)}
                hint={r.emails_failed ? 'After all retries' : 'None'}
              />
              <StatTile label="Retries" value={formatNumber(r.retries)} hint="Provider errors" />
              <StatTile
                label="Model cost"
                value={formatCost(Number(r.cost_usd))}
                hint={sentToModel ? `${formatCost(Number(r.cost_usd) / sentToModel)} per email` : '—'}
              />
              <StatTile
                label="Duration"
                value={ms !== null ? formatDuration(ms) : '—'}
                hint={perMinute ? `${Math.round(perMinute)} emails/min` : 'Not started'}
              />
            </dl>

            {live && (
              <div className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 shadow-xs">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-[width] duration-500"
                    style={{
                      width: `${r.emails_found ? Math.min(100, ((r.emails_processed + r.emails_failed) / r.emails_found) * 100) : 5}%`,
                    }}
                  />
                </div>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {formatNumber(r.emails_processed + r.emails_failed)} / {formatNumber(r.emails_found)}
                </span>
              </div>
            )}

            {insights.isError ? (
              <ErrorBanner message={`Couldn't load insights: ${insights.error.message}`} onRetry={() => insights.refetch()} />
            ) : !insights.data ? (
              <Skeleton className="h-64 rounded-xl" />
            ) : (
              <>
                <div className="grid items-start gap-4 lg:grid-cols-2">
                  {insights.data.labels.map((insight) => (
                    <RunLabelInsightCard key={insight.label_name} insight={insight} nearWindow={insights.data.near_window} />
                  ))}
                  <ChartCard
                    title="Inboxes"
                    description="Emails listed in each inbox"
                    table={
                      <ChartTable
                        columns={['Inbox', 'Emails', 'Error']}
                        rows={r.inboxes.map((i) => [`${i.inbox_name} · ${i.email_address}`, i.emails_found, i.error ?? ''])}
                      />
                    }
                  >
                    <BarList
                      items={r.inboxes.map((i) => ({
                        key: i.email_address,
                        label: i.inbox_name,
                        sublabel: i.error ? `error: ${i.error}` : i.email_address,
                        value: i.emails_found,
                      }))}
                    />
                  </ChartCard>
                </div>

                <ChartCard
                  title="Matched emails over time"
                  description={`${granularityLabel[insights.data.granularity]} · by sent date · labels applied by this run`}
                  table={
                    <ChartTable
                      columns={['Period', 'Matched']}
                      rows={insights.data.matched_timeline.map((b) => [
                        bucketTitle({ ...b, labelled: b.emails }, insights.data.granularity),
                        b.emails,
                      ])}
                    />
                  }
                >
                  <ColumnChart
                    series={[{ key: 'emails', label: 'Matched', className: 'bg-chart-emphasis' }]}
                    data={toColumns(
                      insights.data.matched_timeline.map((b) => ({ ...b, labelled: b.emails })),
                      insights.data.granularity,
                      (b) => ({ emails: b.emails }),
                    )}
                  />
                </ChartCard>
              </>
            )}

            <RunEmailsList
              tab={tab}
              onTab={(next) => update({ tab: next === 'matched' ? null : next })}
              labels={r.labels.filter((l) => l.label_id).map((l) => ({ id: l.label_id as string, name: l.label_name }))}
              labelId={labelId}
              onLabel={(id) => update({ label: id })}
              sort={sort}
              onSort={(next) => update({ sort: next === 'probability_desc' ? null : next })}
              data={emails.data}
              stale={emails.isPlaceholderData}
              onPage={(next) => update({ page: next > 1 ? String(next) : null })}
              thresholds={Object.fromEntries(
                r.labels.filter((l) => l.label_id).map((l) => [l.label_id as string, l.match_threshold]),
              )}
            />

            <p className={cn('flex items-start gap-2 text-xs text-muted-foreground')}>
              <Info className="mt-px size-3.5 shrink-0" />
              Per-email detail shows answers still attributed to this run. If a later run re-asks the same email and
              label, the answer moves to that run; totals above stay as recorded.
            </p>
          </div>
        )}
      </PageBody>
    </>
  )
}
