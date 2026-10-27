import { ChartColumn, Cog } from 'lucide-react'
import { Link } from 'react-router'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorBanner } from '@/components/layout/error-banner'
import { ItemList, ItemRow, MetaDot } from '@/components/layout/item-list'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { FilterStatusBadge } from '@/features/filters/filter-status-badge'
import { LabelDot } from '@/features/labels/label-dot'
import { useDashboards } from './api'

export function DashboardsPage() {
  const { data: dashboards, isPending, isError, error, refetch } = useDashboards()

  return (
    <>
      <PageHeader
        title="Dashboards"
        description="What your processors found in your email: one dashboard per processor."
      />
      <PageBody>
        {isPending ? (
          <Skeleton className="h-40 rounded-xl" />
        ) : isError ? (
          <ErrorBanner message={`Couldn't load dashboards: ${error.message}`} onRetry={() => refetch()} />
        ) : dashboards.length === 0 ? (
          <EmptyState
            icon={ChartColumn}
            title="No dashboards yet"
            description="Every processor gets one. Add a processor to a label, e.g. credit card statements."
            action={
              <Button asChild>
                <Link to="/automation/processors">
                  <Cog />
                  Go to processors
                </Link>
              </Button>
            }
          />
        ) : (
          <ItemList>
            {dashboards.map((dashboard) => (
              <ItemRow
                key={dashboard.id}
                leading={
                  <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
                    <ChartColumn className="size-[18px]" strokeWidth={1.75} />
                  </span>
                }
                title={
                  <Link
                    to={`/dashboards/${dashboard.id}`}
                    className="outline-none after:absolute after:inset-0 focus-visible:underline"
                  >
                    {dashboard.name}
                  </Link>
                }
                badges={dashboard.processor_status === 'inactive' && <FilterStatusBadge status="inactive" />}
                meta={
                  <>
                    <span>{dashboard.kind_name}</span>
                    <MetaDot />
                    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
                      {dashboard.labels.map((label) => (
                        <span key={label.id} className="inline-flex items-center gap-1">
                          <LabelDot color={label.color} />
                          {label.display_name}
                        </span>
                      ))}
                    </span>
                  </>
                }
              >
                <p className="truncate text-sm text-muted-foreground">
                  {dashboard.spec.widgets.length} charts and tables
                </p>
              </ItemRow>
            ))}
          </ItemList>
        )}
      </PageBody>
    </>
  )
}
