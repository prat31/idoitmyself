import { Cog, KeyRound } from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { DefaultBadge } from '@/components/layout/default-badge'
import { Figure, ItemRow, MetaDot } from '@/components/layout/item-list'
import { Switch } from '@/components/ui/switch'
import { FilterStatusBadge } from '@/features/filters/filter-status-badge'
import { LabelDot } from '@/features/labels/label-dot'
import { formatDateTime, formatNumber, formatRelative } from '@/lib/format'
import { useUpdateProcessor, type Processor } from './api'
import { DeleteProcessorDialog } from './delete-processor-dialog'

/** One processor as a list row; the row opens its page (stretched link), the switch (de)activates it. */
export function ProcessorRow({ processor }: { processor: Processor }) {
  const update = useUpdateProcessor()
  const active = processor.status === 'active'

  const toggle = (checked: boolean) =>
    update.mutate(
      { id: processor.id, changes: { status: checked ? 'active' : 'inactive' } },
      {
        onSuccess: () => toast.success(`“${processor.name}” ${checked ? 'activated' : 'deactivated'}`),
        onError: (error) => toast.error("Couldn't change the processor", { description: error.message }),
      },
    )

  return (
    <ItemRow
      leading={
        <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
          <Cog className="size-[18px]" strokeWidth={1.75} />
        </span>
      }
      title={
        <Link
          to={`/automation/processors/${processor.id}`}
          className="outline-none after:absolute after:inset-0 focus-visible:underline"
        >
          {processor.name}
        </Link>
      }
      badges={
        <>
          <FilterStatusBadge status={processor.status} />
          {processor.is_default && <DefaultBadge />}
          {processor.runs.needs_input > 0 && (
            <span className="inline-flex items-center gap-1 rounded-md bg-warning/10 px-1.5 py-0.5 text-[11px] font-medium text-warning">
              <KeyRound className="size-3" />
              Needs input
            </span>
          )}
        </>
      }
      figures={
        <>
          <Figure value={formatNumber(processor.runs.failed)} label="Failed" muted />
          <Figure value={formatNumber(processor.runs.succeeded)} label="Emails" />
          <Figure value={formatNumber(processor.records)} label="Records" />
        </>
      }
      actions={
        <div className="flex items-center gap-1">
          {!processor.is_default && <DeleteProcessorDialog processor={processor} />}
          <Switch
            checked={active}
            disabled={update.isPending}
            onCheckedChange={toggle}
            aria-label={active ? `Deactivate ${processor.name}` : `Activate ${processor.name}`}
          />
        </div>
      }
      meta={
        <>
          <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
            Runs on
            {processor.labels.map((label) => (
              <span key={label.id} className="inline-flex items-center gap-1">
                <LabelDot color={label.color} />
                <span className="font-medium text-foreground">{label.display_name}</span>
              </span>
            ))}
          </span>
          <MetaDot />
          {processor.last_run_at ? (
            <span>
              Last run{' '}
              <time dateTime={processor.last_run_at} title={formatDateTime(processor.last_run_at)}>
                {formatRelative(processor.last_run_at)}
              </time>
            </span>
          ) : (
            <span>Not run yet</span>
          )}
        </>
      }
    >
      <p className="truncate text-sm text-muted-foreground">{processor.description || processor.kind_name}</p>
    </ItemRow>
  )
}
