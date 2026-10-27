import { cn } from '@/lib/utils'
import type { RunStatus } from './api'

const styles: Record<RunStatus, { label: string; className: string }> = {
  queued: { label: 'Queued', className: 'bg-muted text-muted-foreground' },
  running: { label: 'Running', className: 'bg-muted text-foreground' },
  succeeded: { label: 'Succeeded', className: 'bg-success/10 text-success' },
  skipped: { label: 'Skipped', className: 'bg-muted text-muted-foreground' },
  failed: { label: 'Failed', className: 'bg-destructive/10 text-destructive' },
  needs_input: { label: 'Needs input', className: 'bg-warning/10 text-warning' },
  cancelled: { label: 'Cancelled', className: 'bg-muted text-muted-foreground' },
}

export function RunStatusBadge({ status }: { status: RunStatus }) {
  const { label, className } = styles[status]
  return <span className={cn('inline-flex rounded-md px-2 py-0.5 text-xs font-medium', className)}>{label}</span>
}
