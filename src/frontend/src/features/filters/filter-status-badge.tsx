import { cn } from '@/lib/utils'
import type { FilterStatus } from './api'

export function FilterStatusBadge({ status }: { status: FilterStatus }) {
  const active = status === 'active'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium',
        active ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground',
      )}
    >
      <span className={cn('size-1.5 rounded-full', active ? 'bg-success' : 'bg-muted-foreground/60')} aria-hidden="true" />
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}
