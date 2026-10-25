import { Plus, Tag } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorBanner } from '@/components/layout/error-banner'
import { ItemList } from '@/components/layout/item-list'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AddLabelDialog } from './add-label-dialog'
import { useLabels } from './api'
import { LabelRow } from './label-row'

const addButton = (
  <Button>
    <Plus />
    Add label
  </Button>
)

function LoadingState() {
  return (
    <div className="divide-y rounded-xl border bg-card">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-4">
          <Skeleton className="size-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-3/4" />
          </div>
          <Skeleton className="h-8 w-16" />
        </div>
      ))}
    </div>
  )
}

export function LabelsPage() {
  const { data: labels, isPending, isError, error, refetch } = useLabels()
  const hasLabels = !!labels && labels.length > 0

  return (
    <>
      <PageHeader
        title="Labels"
        description="Filters add labels to the emails they match, across every inbox."
        actions={hasLabels ? <AddLabelDialog trigger={addButton} /> : undefined}
      />
      <PageBody>
        {isPending ? (
          <LoadingState />
        ) : isError ? (
          <ErrorBanner message={`Couldn't load labels: ${error.message}`} onRetry={() => refetch()} />
        ) : hasLabels ? (
          <ItemList>
            {labels.map((label) => (
              <LabelRow key={label.id} label={label} />
            ))}
          </ItemList>
        ) : (
          <EmptyState
            icon={Tag}
            title="No labels yet"
            description="Create a label here, or while creating a filter. Every filter adds one label."
            action={<AddLabelDialog trigger={addButton} />}
          />
        )}
      </PageBody>
    </>
  )
}
