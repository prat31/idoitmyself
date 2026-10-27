import { useMemo, useState } from 'react'
import { ArrowLeft, CalendarRange, Cog } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { LabelDot } from '@/features/labels/label-dot'
import { cn } from '@/lib/utils'
import { useDashboard, useDatasets, type DashboardRange, type QueryScope } from './api'
import { previousPeriod, rangeLabels, rangeStart, widgetSpan } from './values'
import { WidgetView } from './widgets'

export function DashboardPage() {
  const { dashboardId = '' } = useParams()
  const dashboard = useDashboard(dashboardId)
  const datasets = useDatasets()
  const [chosenRange, setRange] = useState<DashboardRange | null>(null)
  const range = chosenRange ?? dashboard.data?.spec.default_range ?? '12m'

  const { scope, previous, start } = useMemo(() => {
    const ids = [dashboardId]
    const start = rangeStart(range)
    const before = previousPeriod(range)
    return {
      start,
      scope: { processor_ids: ids, start: start?.toISOString() ?? null, end: null } satisfies QueryScope,
      previous: before
        ? ({ processor_ids: ids, start: before.start.toISOString(), end: before.end.toISOString() } satisfies QueryScope)
        : null,
    }
  }, [dashboardId, range])

  const backLink = (
    <Link
      to="/dashboards"
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="size-4" />
      Dashboards
    </Link>
  )

  if (dashboard.isError) {
    return (
      <PageBody>
        <div className="space-y-4">
          {backLink}
          <ErrorBanner message={`Couldn't load the dashboard: ${dashboard.error.message}`} onRetry={() => dashboard.refetch()} />
        </div>
      </PageBody>
    )
  }

  const data = dashboard.data
  return (
    <>
      <header className="space-y-4 border-b px-4 pb-5 pt-6 md:px-10 md:pb-6 md:pt-8">
        {backLink}
        {!data ? (
          <Skeleton className="h-9 w-64" />
        ) : (
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div className="min-w-0 flex-1 space-y-1">
              <h1 className="truncate font-serif text-2xl font-semibold tracking-tight md:text-3xl">{data.name}</h1>
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                {data.kind_name} · runs on
                {data.labels.map((label) => (
                  <span key={label.id} className="inline-flex items-center gap-1 text-foreground">
                    <LabelDot color={label.color} />
                    {label.display_name}
                  </span>
                ))}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Select value={range} onValueChange={(value) => setRange(value as DashboardRange)}>
                <SelectTrigger aria-label="Date range" className="w-auto gap-2">
                  <CalendarRange className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent align="end">
                  {(Object.keys(rangeLabels) as DashboardRange[]).map((value) => (
                    <SelectItem key={value} value={value}>
                      {rangeLabels[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" asChild>
                <Link to={`/automation/processors/${data.id}`} aria-label="Open the processor" title="Open the processor">
                  <Cog />
                </Link>
              </Button>
            </div>
          </div>
        )}
      </header>

      <PageBody>
        {!data || datasets.isPending ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-[84px] rounded-xl" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-6">
            {data.spec.widgets.map((widget) => (
              <div key={widget.id} className={cn('min-w-0', widgetSpan[widget.width])}>
                <WidgetView
                  widget={widget}
                  dataset={datasets.data?.find((d) => d.name === widget.query.dataset)}
                  scope={scope}
                  previous={previous}
                  start={start}
                />
              </div>
            ))}
          </div>
        )}
      </PageBody>
    </>
  )
}
