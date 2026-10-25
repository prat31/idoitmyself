import { Loader2 } from 'lucide-react'

import { useActiveScans } from './api'

/** Spinner beside "Scans" in the sidebar while any scan is queued or running. */
export function ScansActivityIndicator() {
  const { data } = useActiveScans()
  const active = data?.total ?? 0
  if (!active) return null
  const label = active === 1 ? '1 scan in progress' : `${active} scans in progress`
  return (
    <span className="ml-auto flex items-center" title={label}>
      <Loader2 className="size-3.5 animate-spin text-muted-foreground" aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </span>
  )
}
