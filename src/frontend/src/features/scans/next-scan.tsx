import { useEffect, useState } from 'react'
import { Clock } from 'lucide-react'

import { formatDayMonth, formatTime } from '@/lib/format'
import { useScanSchedule } from './api'
import { intervalLabel } from './interval'

function untilText(ms: number): string {
  const minutes = Math.ceil(ms / 60_000)
  if (minutes <= 1) return 'in under a minute'
  if (minutes < 60) return `in ${minutes} minutes`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return `in ${hours} ${hours === 1 ? 'hour' : 'hours'}${rest ? ` ${rest} min` : ''}`
}

/** "3:30 pm", or "26 Oct, 12:00 am" when it isn't today. */
function whenText(iso: string): string {
  const today = new Date(iso).toDateString() === new Date().toDateString()
  return today ? formatTime(iso) : `${formatDayMonth(iso)}, ${formatTime(iso)}`
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
    <span className="inline-flex items-center gap-1.5" title={`Scheduled scans run ${intervalLabel(data.interval_minutes)}`}>
      <Clock className="size-3.5 shrink-0" aria-hidden="true" />
      Next scan {remaining > 0 ? untilText(remaining) : 'starting now'} ({whenText(data.next_run_at)})
    </span>
  )
}
