import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import { useActiveScans, type Scan } from '@/features/scans/api'
import { timeZone } from '@/features/stats/api'

export type DashboardSummary = {
  scans_completed: number
  scans_failed: number
  /** New emails fetched and filtered (excludes ones already stored). */
  emails_scanned: number
  /** Emails that got at least one label (one email can get several). */
  emails_labelled: number
  active_filters: number
  inactive_filters: number
  label_months: { label_id: string; display_name: string; color: string; this_month: number; last_month: number }[]
}

type AttentionInbox = { inbox_id: string; name: string; email_address: string; error: string; scan_id: string | null }

export type DashboardAttention = {
  /** The inbox's latest finished scan failed. */
  inboxes_with_errors: AttentionInbox[]
  /** Failed, or completed with failed emails (last 30 days). */
  scans_with_problems: {
    scan_id: string
    inbox_name: string
    status: string
    emails_failed: number
    error: string | null
    created_at: string
  }[]
  /** Active, but haven't labelled anything yet. */
  filters_never_matched: { filter_id: string; name: string; label_display_name: string }[]
  /** No active filter adds them any more. */
  labels_without_active_filter: { label_id: string; display_name: string; color: string }[]
  /** No active filter covers the inbox, so it isn't scanned. */
  inboxes_without_filters: AttentionInbox[]
}

/** Everything the Needs attention section would list; 0 means the section is left out. */
export function attentionCount(data: DashboardAttention): number {
  return (
    data.inboxes_with_errors.length +
    data.scans_with_problems.length +
    data.inboxes_without_filters.length +
    data.filters_never_matched.length +
    data.labels_without_active_filter.length
  )
}

export type DashboardStatus = {
  scan_interval_minutes: number
  inboxes: {
    inbox_id: string
    name: string
    email_address: string
    provider: string
    /** End of the last scheduled scan's window. */
    scanned_until: string | null
    last_completed_scan_at: string | null
    active_scan: Scan | null
    quota_used: number
    quota_limit: number
    quota_window_seconds: number
  }[]
}

export type DashboardRecent = {
  matches: {
    email_id: string
    sent_at: string
    from_address: string | null
    subject: string | null
    inbox_name: string
    label_id: string
    label_display_name: string
    label_color: string
    filter_name: string | null
    applied_at: string
    /** Opens the message in its provider's web UI (null if there's none). */
    open_url: string | null
  }[]
}

const key = ['dashboard'] as const

export function useDashboardSummary(start: string | null, end: string | null, refetchInterval?: number) {
  const params = new URLSearchParams({ tz: timeZone })
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  return useQuery({
    queryKey: [...key, 'summary', params.toString()],
    queryFn: () => apiFetch<DashboardSummary>(`/dashboard/summary?${params}`),
    placeholderData: keepPreviousData,
    refetchInterval,
  })
}

export function useDashboardAttention(refetchInterval?: number) {
  return useQuery({
    queryKey: [...key, 'attention'],
    queryFn: () => apiFetch<DashboardAttention>('/dashboard/attention'),
    refetchInterval,
  })
}

export function useDashboardStatus(refetchInterval?: number) {
  return useQuery({
    queryKey: [...key, 'status'],
    queryFn: () => apiFetch<DashboardStatus>('/dashboard/status'),
    refetchInterval,
  })
}

export function useDashboardRecent(limit = 5, refetchInterval?: number) {
  return useQuery({
    queryKey: [...key, 'recent', limit],
    queryFn: () => apiFetch<DashboardRecent>(`/dashboard/recent?limit=${limit}`),
    refetchInterval,
  })
}

/** How often the dashboard refreshes: every few seconds while a scan is working (counts move by the
 *  second), otherwise every 30 seconds (scans start on the server's schedule). */
export function useLiveInterval(): number {
  const { data } = useActiveScans()
  return data?.total ? 5_000 : 30_000
}
