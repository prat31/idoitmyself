import { History } from 'lucide-react'

import { Checkbox } from '@/components/ui/checkbox'
import { formatDate, formatNumber } from '@/lib/format'
import type { RunCoverage } from './api'

function rangeLabel(range: { start: string; end: string }): string {
  // `end` is exclusive (midnight after the last covered day).
  const first = formatDate(range.start)
  const last = formatDate(new Date(new Date(range.end).getTime() - 1))
  return first === last ? first : `${first} – ${last}`
}

/** Tells the user which parts of the chosen range were already scanned, and offers to re-classify. */
export function CoverageNotice({
  coverage,
  reclassify,
  onReclassifyChange,
}: {
  coverage: RunCoverage
  reclassify: boolean
  onReclassifyChange: (value: boolean) => void
}) {
  const scanned = coverage.labels.filter((l) => l.covered.length > 0 || l.evaluated_emails > 0)
  if (scanned.length === 0) return null

  return (
    <div className="space-y-3 rounded-lg border bg-muted/40 p-3">
      <div className="flex items-start gap-2">
        <History className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0 space-y-1.5 text-sm">
          <p className="font-medium">Part of this range was already scanned</p>
          <ul className="space-y-1 text-xs text-muted-foreground">
            {scanned.map((label) => (
              <li key={label.label_id}>
                <span className="font-mono font-medium text-foreground">{label.label_name}</span>
                {label.covered.length > 0 ? ` · ${label.covered.map(rangeLabel).join(', ')}` : ''}
                {label.evaluated_emails > 0 && ` · ${formatNumber(label.evaluated_emails)} emails already answered`}
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            {reclassify
              ? 'Every email in the range will be fetched and sent to the model again, costing AI for each.'
              : "Emails already answered for a label won't be sent to the model again: only new emails, and labels they haven't been asked about, cost AI."}
          </p>
        </div>
      </div>
      <label className="flex cursor-pointer items-start gap-2.5 border-t pt-3 text-sm">
        <Checkbox className="mt-0.5" checked={reclassify} onCheckedChange={(on) => onReclassifyChange(on === true)} />
        <span>
          Re-classify already scanned emails
          <span className="block text-xs text-muted-foreground">Ask the model again and replace earlier answers.</span>
        </span>
      </label>
    </div>
  )
}
