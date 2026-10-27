import { Repeat } from 'lucide-react'
import { toast } from 'sonner'

import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useScanSchedule, useUpdateScanSchedule } from './api'
import { intervalLabel, intervalTitle } from './interval'

/** Picks how often scheduled scans run. Saved at once; applies from the next tick. */
export function ScanIntervalSelect() {
  const { data } = useScanSchedule()
  const update = useUpdateScanSchedule()
  if (!data) return null

  const change = (value: string) =>
    update.mutate(Number(value), {
      onSuccess: (schedule) => toast.success(`Scheduled scans now run ${intervalLabel(schedule.interval_minutes)}`),
      onError: (error) => toast.error("Couldn't change the schedule", { description: error.message }),
    })

  return (
    <Select value={String(data.interval_minutes)} onValueChange={change} disabled={update.isPending}>
      <SelectTrigger aria-label="How often scheduled scans run" className="w-auto gap-2">
        <Repeat className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="end">
        <SelectGroup>
          <SelectLabel>Scheduled scans, from midnight {data.timezone}</SelectLabel>
          {data.intervals.map((minutes) => (
            <SelectItem key={minutes} value={String(minutes)}>
              {intervalTitle(minutes)}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}
