import { ListFilter, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router'

import { Figure, ItemRow } from '@/components/layout/item-list'
import { formatNumber } from '@/lib/format'
import type { Label } from './api'
import { DeleteLabelDialog } from './delete-label-dialog'
import { EditLabelDialog } from './edit-label-dialog'
import { LabelDot } from './label-dot'

/** One label as a list row; the whole row opens the label's page (stretched link). */
export function LabelRow({ label }: { label: Label }) {
  const active = label.filters.filter((f) => f.status === 'active')
  return (
    <ItemRow
      leading={
        <span className="flex size-9 items-center justify-center rounded-lg bg-secondary">
          <LabelDot color={label.color} className="size-3" />
        </span>
      }
      title={
        <Link to={`/automation/labels/${label.id}`} className="outline-none after:absolute after:inset-0 focus-visible:underline">
          {label.display_name}
        </Link>
      }
      badges={
        active.length === 0 && (
          <span className="inline-flex items-center gap-1 rounded-md bg-warning/10 px-1.5 py-0.5 text-[11px] font-medium text-warning">
            <TriangleAlert className="size-3" />
            No active filter
          </span>
        )
      }
      figures={
        <>
          <Figure value={formatNumber(label.filters.length)} label="Filters" muted />
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
      {label.filters.length > 0 && (
        <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <ListFilter className="mt-0.5 size-3 shrink-0" aria-label="Added by" />
          <span className="line-clamp-2">
            {label.filters.map((f, i) => (
              <span key={f.id}>
                {i > 0 && ', '}
                {f.name}
                {f.status === 'inactive' && <span className="text-muted-foreground/70"> (inactive)</span>}
              </span>
            ))}
          </span>
        </p>
      )}
    </ItemRow>
  )
}
