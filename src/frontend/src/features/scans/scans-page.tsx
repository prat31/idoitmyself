import { ChevronLeft, ChevronRight, Plus, ScanSearch } from 'lucide-react'
import { useSearchParams } from 'react-router'

import { EmptyState } from '@/components/layout/empty-state'
import { ErrorBanner } from '@/components/layout/error-banner'
import { ItemList } from '@/components/layout/item-list'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useScans } from './api'
import { NewScanDialog } from './new-scan-dialog'
import { NextScan } from './next-scan'
import { ScanRow } from './scan-row'

const PAGE_SIZE = 25

const newScanButton = (
  <Button>
    <Plus />
    New scan
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

export function ScansPage() {
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const { data, isPending, isError, error, refetch, isPlaceholderData } = useScans(page, PAGE_SIZE)
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1
  const goTo = (next: number) => setParams(next > 1 ? { page: String(next) } : {})

  return (
    <>
      <PageHeader
        title="Scans"
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>Scheduled scans run every 30 minutes.</span>
            <NextScan />
          </span>
        }
        actions={<NewScanDialog trigger={newScanButton} />}
      />
      <PageBody>
        {isPending ? (
          <LoadingState />
        ) : isError ? (
          <ErrorBanner message={`Couldn't load scans: ${error.message}`} onRetry={() => refetch()} />
        ) : data.total > 0 ? (
          <div className="space-y-3">
            <ItemList className={cn('transition-opacity', isPlaceholderData && 'opacity-60')}>
              {data.items.map((scan) => (
                <ScanRow key={scan.id} scan={scan} />
              ))}
            </ItemList>
            {pages > 1 && (
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs tabular-nums text-muted-foreground">
                  Page {data.page} of {pages}
                </span>
                <div className="flex gap-1.5">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => goTo(page - 1)}>
                    <ChevronLeft />
                    Previous
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => goTo(page + 1)}>
                    Next
                    <ChevronRight />
                  </Button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState
            icon={ScanSearch}
            title="No scans yet"
            description="Scans start on their own at the next :00 or :30 once an inbox is connected and an active filter covers it."
          />
        )}
      </PageBody>
    </>
  )
}
