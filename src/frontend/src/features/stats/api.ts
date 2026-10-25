import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'

export type Granularity = 'day' | 'week' | 'month'

export type TimelineBucket = { start: string; emails: number; labelled: number }
export type InboxCount = { inbox_id: string; name: string; email_address: string; emails: number }
export type SenderCount = { sender: string; emails: number }
export type LabelCount = { label_id: string; name: string; display_name: string; color: string; emails: number }
/** Emails a filter labelled. */
export type FilterCount = { filter_id: string; name: string; label_display_name: string; emails: number }

export type Overview = {
  window_start: string | null
  window_end: string | null
  granularity: Granularity
  totals: { emails: number; labelled_emails: number; label_assignments: number; senders: number }
  timeline: TimelineBucket[]
  by_label: LabelCount[]
  by_filter: FilterCount[]
  by_inbox: InboxCount[]
  top_senders: SenderCount[]
}

export type OverviewFilters = {
  start: string | null
  end: string | null
  inboxId: string | null
  labelIds: string[]
}

export const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone

/** `refetchInterval` keeps it live (ms), e.g. on the dashboard. */
export function useOverview(filters: OverviewFilters, refetchInterval?: number) {
  const params = new URLSearchParams({ tz: timeZone })
  if (filters.start) params.set('start', filters.start)
  if (filters.end) params.set('end', filters.end)
  if (filters.inboxId) params.set('inbox_id', filters.inboxId)
  filters.labelIds.forEach((id) => params.append('label_id', id))
  return useQuery({
    queryKey: ['stats', 'overview', params.toString()],
    queryFn: () => apiFetch<Overview>(`/stats/overview?${params}`),
    placeholderData: keepPreviousData, // keep the frame while filters refetch
    refetchInterval,
  })
}
