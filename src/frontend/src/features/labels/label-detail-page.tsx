import { ArrowLeft, ListFilter, TriangleAlert } from 'lucide-react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'

import { BarList } from '@/components/charts/bar-list'
import { ChartCard, ChartTable } from '@/components/charts/chart-card'
import { ColumnChart } from '@/components/charts/column-chart'
import { StatTile } from '@/components/charts/stat-tile'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { Skeleton } from '@/components/ui/skeleton'
import { bucketTitle, granularityLabel, toColumns } from '@/features/stats/timeline'
import { formatDate, formatDayMonth, formatNumber, formatSender, senderAddress } from '@/lib/format'
import { useLabel, useLabelEmails, useLabelStats } from './api'
import { DeleteLabelDialog } from './delete-label-dialog'
import { EditLabelDialog } from './edit-label-dialog'
import { LabelDot } from './label-dot'
import { LabelEmailsTable } from './label-emails-table'
import { NormalizedName } from './label-name-field'

const PAGE_SIZE = 25

export function LabelDetailPage() {
  const { labelId = '' } = useParams()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)

  const label = useLabel(labelId)
  const stats = useLabelStats(labelId)
  const emails = useLabelEmails(labelId, page, PAGE_SIZE)

  const backLink = (
    <Link
      to="/automation/labels"
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" />
      Labels
    </Link>
  )

  if (label.isError) {
    return (
      <PageBody>
        <div className="space-y-4">
          {backLink}
          <ErrorBanner message={`Couldn't load the label: ${label.error.message}`} onRetry={() => label.refetch()} />
        </div>
      </PageBody>
    )
  }

  return (
    <>
      <header className="space-y-4 border-b px-4 pb-5 pt-6 md:px-10 md:pb-6 md:pt-8">
        {backLink}
        {label.isPending ? (
          <Skeleton className="h-9 w-64" />
        ) : (
          <div className="flex items-start gap-3">
            <span className="mt-1 flex size-10 shrink-0 items-center justify-center rounded-lg bg-secondary">
              <LabelDot color={label.data.color} className="size-3.5" />
            </span>
            <div className="min-w-0 flex-1 space-y-1">
              <h1 className="truncate font-serif text-2xl font-semibold tracking-tight md:text-3xl">
                {label.data.display_name}
              </h1>
              <p className="text-sm text-muted-foreground">
                Normalised name <NormalizedName name={label.data.name} />
              </p>
              {label.data.filters.length > 0 ? (
                <p className="flex flex-wrap items-center gap-1.5 pt-1 text-sm text-muted-foreground">
                  <ListFilter className="size-3.5 shrink-0" aria-hidden="true" />
                  Added by
                  {label.data.filters.map((f, i) => (
                    <span key={f.id}>
                      <Link to={`/automation/filters/${f.id}`} className="text-foreground underline-offset-2 hover:underline">
                        {f.name}
                      </Link>
                      {f.status === 'inactive' && ' (inactive)'}
                      {i < label.data.filters.length - 1 && ','}
                    </span>
                  ))}
                </p>
              ) : (
                <p className="mt-1 inline-flex items-center gap-1.5 rounded-md bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
                  <TriangleAlert className="size-3.5" />
                  No filter adds this label
                </p>
              )}
            </div>
            <div className="flex shrink-0 items-center">
              <EditLabelDialog label={label.data} />
              <DeleteLabelDialog label={label.data} onDeleted={() => navigate('/automation/labels')} />
            </div>
          </div>
        )}
      </header>

      <PageBody>
        <div className="space-y-4">
          {stats.isError ? (
            <ErrorBanner message={`Couldn't load stats: ${stats.error.message}`} onRetry={() => stats.refetch()} />
          ) : stats.isPending ? (
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-[84px] rounded-xl" />
              ))}
            </div>
          ) : (
            <>
              <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <StatTile label="Emails" value={formatNumber(stats.data.emails)} hint="Across all inboxes" />
                <StatTile label="Last 30 days" value={formatNumber(stats.data.emails_last_30_days)} hint="By sent date" />
                <StatTile
                  label="Filters"
                  value={formatNumber(label.data?.filters.filter((f) => f.status === 'active').length ?? 0)}
                  hint={`Active, of ${formatNumber(label.data?.filters.length ?? 0)}`}
                />
                <StatTile
                  label="Latest email"
                  value={stats.data.last_sent_at ? formatDayMonth(stats.data.last_sent_at) : '—'}
                  hint={stats.data.first_sent_at ? `First ${formatDate(stats.data.first_sent_at)}` : 'No emails yet'}
                />
              </dl>

              {stats.data.emails > 0 && (
                <>
                  <ChartCard
                    title="Emails over time"
                    description={`${granularityLabel[stats.data.granularity]} · by sent date`}
                    table={
                      <ChartTable
                        columns={['Period', 'Emails']}
                        rows={stats.data.timeline.map((b) => [bucketTitle(b, stats.data.granularity), b.emails])}
                      />
                    }
                  >
                    <ColumnChart
                      series={[{ key: 'emails', label: 'Emails', className: 'bg-chart-emphasis' }]}
                      data={toColumns(stats.data.timeline, stats.data.granularity, (b) => ({ emails: b.emails }))}
                    />
                  </ChartCard>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <ChartCard
                      title="By filter"
                      description="Which filter added the label"
                      table={
                        <ChartTable columns={['Filter', 'Emails']} rows={stats.data.by_filter.map((f) => [f.name, f.emails])} />
                      }
                    >
                      <BarList items={stats.data.by_filter.map((f) => ({ key: f.filter_id, label: f.name, value: f.emails }))} />
                    </ChartCard>
                    <ChartCard
                      title="Top senders"
                      table={
                        <ChartTable
                          columns={['Sender', 'Emails']}
                          rows={stats.data.top_senders.map((s) => [s.sender, s.emails])}
                        />
                      }
                    >
                      <BarList
                        items={stats.data.top_senders.map((s) => ({
                          key: s.sender,
                          label: formatSender(s.sender),
                          sublabel: senderAddress(s.sender) ?? undefined,
                          title: s.sender,
                          value: s.emails,
                        }))}
                      />
                    </ChartCard>
                    <ChartCard
                      title="By inbox"
                      table={
                        <ChartTable columns={['Inbox', 'Emails']} rows={stats.data.by_inbox.map((i) => [i.name, i.emails])} />
                      }
                    >
                      <BarList
                        items={stats.data.by_inbox.map((i) => ({
                          key: i.inbox_id,
                          label: `${i.name} · ${i.email_address}`,
                          value: i.emails,
                        }))}
                      />
                    </ChartCard>
                  </div>
                </>
              )}
            </>
          )}

          {emails.isError ? (
            <ErrorBanner message={`Couldn't load emails: ${emails.error.message}`} onRetry={() => emails.refetch()} />
          ) : emails.isPending ? (
            <Skeleton className="h-48 rounded-xl" />
          ) : (
            <LabelEmailsTable
              data={emails.data}
              stale={emails.isPlaceholderData}
              onPage={(next) => setParams(next > 1 ? { page: String(next) } : {}, { replace: false })}
            />
          )}
        </div>
      </PageBody>
    </>
  )
}
