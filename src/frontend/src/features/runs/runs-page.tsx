import { Play, PlayCircle } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorBanner } from '@/components/layout/error-banner'
import { ItemList } from '@/components/layout/item-list'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useRuns } from './api'
import { NewRunDialog } from './new-run-dialog'
import { RunRow } from './run-row'

const newRunButton = (
  <Button>
    <Play />
    New run
  </Button>
)

function LoadingState() {
  return (
    <div className="divide-y rounded-xl border bg-card">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-8 w-56" />
        </div>
      ))}
    </div>
  )
}

export function RunsPage() {
  const { data: runs, isPending, isError, error, refetch } = useRuns()
  const hasRuns = !!runs && runs.length > 0

  return (
    <>
      <PageHeader
        title="Runs"
        description="Classify email in a date range against your labels. Every run, newest first."
        actions={hasRuns ? <NewRunDialog trigger={newRunButton} /> : undefined}
      />
      <PageBody>
        {isPending ? (
          <LoadingState />
        ) : isError ? (
          <ErrorBanner message={`Couldn't load runs: ${error.message}`} onRetry={() => refetch()} />
        ) : hasRuns ? (
          <ItemList>
            {runs.map((run) => (
              <RunRow key={run.id} run={run} />
            ))}
          </ItemList>
        ) : (
          <EmptyState
            icon={PlayCircle}
            title="No runs yet"
            description="Start an ad hoc run to fetch email from a date range and label it with the model."
            action={<NewRunDialog trigger={newRunButton} />}
          />
        )}
      </PageBody>
    </>
  )
}
