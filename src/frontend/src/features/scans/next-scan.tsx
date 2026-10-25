import { useEffect, useState } from 'react'
import { Clock } from 'lucide-react'

import { formatTime } from '@/lib/format'
import { useScanSchedule } from './api'

function untilText(ms: number): string {
  const minutes = Math.ceil(ms / 60_000)
  if (minutes <= 1) return 'in under a minute'
  return `in ${minutes} minutes`
}

/** "Next scan in 12 minutes (3:30 pm)", kept current while it's on screen. */
export function NextScan() {
  const { data } = useScanSchedule()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15_000)
    return () => window.clearInterval(timer)
  }, [])
  if (!data) return null
  const remaining = new Date(data.next_run_at).getTime() - now
  return (
    <span className="inline-flex items-center gap-1.5" title={`Scheduled scans run every ${data.interval_minutes} minutes`}>
      <Clock className="size-3.5 shrink-0" aria-hidden="true" />
      Next scan {remaining > 0 ? untilText(remaining) : 'starting now'} ({formatTime(data.next_run_at)})
    </span>
  )
}
