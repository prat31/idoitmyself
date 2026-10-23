import { Filter, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router'

import { Figure, ItemRow } from '@/components/layout/item-list'
import { formatNumber } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { Label } from './api'
import { labelColorClass } from './colors'
import { DeleteLabelDialog } from './delete-label-dialog'
import { EditLabelDialog } from './edit-label-dialog'

/** One label as a list row; the whole row opens the label's page (stretched link). */
export function LabelRow({ label }: { label: Label }) {
  return (
    <ItemRow
      leading={
        <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
          <span className={cn('size-3 rounded-full', labelColorClass[label.color])} aria-hidden="true" />
        </span>
      }
      title={
        <Link to={`/discovery/labels/${label.id}`} className="font-mono outline-none after:absolute after:inset-0 focus-visible:underline">
          {label.name}
        </Link>
      }
      badges={
        !label.filter_condition && (
          <span className="inline-flex items-center gap-1 rounded-md bg-warning/10 px-1.5 py-0.5 text-[11px] font-medium text-warning">
            <TriangleAlert className="size-3" />
            No filter condition
          </span>
        )
      }
      figures={
        <>
          {label.filter_condition && <Figure value={`≥ ${label.match_threshold.toFixed(2)}`} label="Match" muted />}
          <Figure value={formatNumber(label.email_count)} label="Emails" />
        </>
      }
      actions={
        <>
          <EditLabelDialog label={label} />
          <DeleteLabelDialog label={label} />
        </>
      }
    >
      {label.description && <p className="truncate text-sm text-muted-foreground">{label.description}</p>}
      {label.filter_condition && (
        <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <Filter className="mt-0.5 size-3 shrink-0" aria-label="Filter condition" />
          <span className="line-clamp-2">{label.filter_condition}</span>
        </p>
      )}
    </ItemRow>
  )
}
