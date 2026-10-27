import { ListFilter, Plus } from 'lucide-react'
import { Link } from 'react-router'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorBanner } from '@/components/layout/error-banner'
import { ItemList } from '@/components/layout/item-list'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useFieldCatalogue, useFilters } from './api'
import { FilterRow } from './filter-row'

const newButton = (
  <Button asChild>
    <Link to="/automation/filters/new">
      <Plus />
      New filter
    </Link>
  </Button>
)

function LoadingState() {
  return (
    <div className="divide-y rounded-xl border bg-card">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-4">
          <Skeleton className="size-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-3/4" />
          </div>
          <Skeleton className="h-6 w-11 rounded-full" />
        </div>
      ))}
    </div>
  )
}

export function FiltersPage() {
  const { data: filters, isPending, isError, error, refetch } = useFilters()
  const { data: catalogue } = useFieldCatalogue()
  const hasFilters = !!filters && filters.length > 0

  return (
    <>
      <PageHeader
        title="Filters"
        description="Rules over sender, subject, attachments and more. Every new email that passes an active filter gets its label."
        actions={hasFilters ? newButton : undefined}
      />
      <PageBody>
        {isPending ? (
          <LoadingState />
        ) : isError ? (
          <ErrorBanner message={`Couldn't load filters: ${error.message}`} onRetry={() => refetch()} />
        ) : hasFilters ? (
          <ItemList>
            {filters.map((filter) => (
              <FilterRow key={filter.id} filter={filter} catalogue={catalogue} />
            ))}
          </ItemList>
        ) : (
          <EmptyState
            icon={ListFilter}
            title="No filters yet"
            description="Create a filter to label new email automatically. Inboxes are scanned on a schedule once a filter is active."
            action={newButton}
          />
        )}
      </PageBody>
    </>
  )
}
