import { Loader2 } from 'lucide-react'

import { useRuns } from './api'

/** Spinner beside "Runs" in the sidebar while any run is queued or running. Shares the Runs page's
 *  query, which polls every 2s while a run is in flight and stops when none are. */
export function RunsActivityIndicator() {
  const { data: runs } = useRuns()
  const active = runs?.filter((run) => run.status === 'queued' || run.status === 'running').length ?? 0
  if (!active) return null
  const label = active === 1 ? '1 run in progress' : `${active} runs in progress`
  return (
    <span className="ml-auto flex items-center" title={label}>
      <Loader2 className="size-3.5 animate-spin text-muted-foreground" aria-hidden="true" />
      <span className="sr-only">{label}</span>
    </span>
  )
}
