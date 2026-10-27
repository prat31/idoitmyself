import { Cog, Plus } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorBanner } from '@/components/layout/error-banner'
import { ItemList } from '@/components/layout/item-list'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ProcessorDialog } from './processor-dialog'
import { useProcessors } from './api'
import { ProcessorRow } from './processor-row'

const addButton = (
  <Button>
    <Plus />
    Add processor
  </Button>
)

export function ProcessorsPage() {
  const { data: processors, isPending, isError, error, refetch } = useProcessors()
  const hasProcessors = !!processors && processors.length > 0

  return (
    <>
      <PageHeader
        title="Processors"
        description="When an email gets one of their labels, processors read it and write records for dashboards. Nothing is sent to any AI."
        actions={hasProcessors ? <ProcessorDialog trigger={addButton} /> : undefined}
      />
      <PageBody>
        {isPending ? (
          <div className="divide-y rounded-xl border bg-card">
            {Array.from({ length: 3 }, (_, i) => (
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
        ) : isError ? (
          <ErrorBanner message={`Couldn't load processors: ${error.message}`} onRetry={() => refetch()} />
        ) : hasProcessors ? (
          <ItemList>
            {processors.map((processor) => (
              <ProcessorRow key={processor.id} processor={processor} />
            ))}
          </ItemList>
        ) : (
          <EmptyState
            icon={Cog}
            title="No processors yet"
            description="Add one to your labels, e.g. read the statement PDF of every credit card bill."
            action={<ProcessorDialog trigger={addButton} />}
          />
        )}
      </PageBody>
    </>
  )
}
