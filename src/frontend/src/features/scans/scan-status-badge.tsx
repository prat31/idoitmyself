import { CircleCheck, CircleDashed, CircleSlash, CircleX, Loader2 } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { ScanStatus } from './api'

const config: Record<ScanStatus, { label: string; icon: typeof CircleCheck; className: string; spin?: boolean }> = {
  queued: { label: 'Queued', icon: CircleDashed, className: 'bg-muted text-muted-foreground' },
  running: { label: 'Running', icon: Loader2, className: 'bg-primary/10 text-foreground', spin: true },
  completed: { label: 'Completed', icon: CircleCheck, className: 'bg-success/10 text-success' },
  failed: { label: 'Failed', icon: CircleX, className: 'bg-destructive/10 text-destructive' },
  cancelled: { label: 'Cancelled', icon: CircleSlash, className: 'bg-muted text-muted-foreground' },
}

export function ScanStatusBadge({ status }: { status: ScanStatus }) {
  const { label, icon: Icon, className, spin } = config[status]
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium', className)}>
      <Icon className={cn('size-3.5', spin && 'animate-spin')} />
      {label}
    </span>
  )
}
