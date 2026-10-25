import { Inbox as InboxIcon, Plus } from 'lucide-react'

import { EmptyState } from '@/components/layout/empty-state'
import { ItemList } from '@/components/layout/item-list'
import { ErrorBanner } from '@/components/layout/error-banner'
import { PageBody } from '@/components/layout/page-body'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AddInboxDialog } from './add-inbox-dialog'
import { useInboxes } from './api'
import { InboxRow } from './inbox-row'
import { useOAuthResultToast } from './use-oauth-result-toast'

const addButton = (
  <Button>
    <Plus />
    Add inbox
  </Button>
)

function LoadingState() {
  return (
    <div className="divide-y rounded-xl border bg-card">
      {Array.from({ length: 3 }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-5 py-4">
          <Skeleton className="size-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-8 w-24" />
        </div>
      ))}
    </div>
  )
}

export function InboxesPage() {
  useOAuthResultToast()
  const { data: inboxes, isPending, isError, error, refetch } = useInboxes()
  const hasInboxes = !!inboxes && inboxes.length > 0

  return (
    <>
      <PageHeader
        title="Inboxes"
        description="Email accounts connected to IDIM. Each is scanned every 30 minutes by the active filters that cover it."
        actions={hasInboxes ? <AddInboxDialog trigger={addButton} /> : undefined}
      />
      <PageBody>
        {isPending ? (
          <LoadingState />
        ) : isError ? (
          <ErrorBanner message={`Couldn't load inboxes: ${error.message}`} onRetry={() => refetch()} />
        ) : hasInboxes ? (
          <ItemList>
            {inboxes.map((inbox) => (
              <InboxRow key={inbox.id} inbox={inbox} />
            ))}
          </ItemList>
        ) : (
          <EmptyState
            icon={InboxIcon}
            title="No inboxes yet"
            description="Connect an email account so IDIM can start reading and organising it."
            action={<AddInboxDialog trigger={addButton} />}
          />
        )}
      </PageBody>
    </>
  )
}
