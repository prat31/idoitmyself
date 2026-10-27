import { Lock } from 'lucide-react'

/** Marks a built-in default (shipped with IDIM): it can be edited, and filters and processors can be
 *  deactivated, but it can't be deleted. */
export function DefaultBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground"
      title="Built-in default: you can edit it, but not delete it"
    >
      <Lock className="size-3" aria-hidden="true" />
      Default
    </span>
  )
}
