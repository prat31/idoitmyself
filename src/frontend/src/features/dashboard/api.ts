import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { LabelColor } from '@/features/labels/colors'
import { timeZone } from '@/features/stats/api'

type LabelRef = { label_id: string; name: string; color: LabelColor; count: number | null }

export type DashboardSummary = {
  runs_completed: number
  runs_failed: number
  cost_usd: string
  emails_sent_to_model: number
  emails_skipped: number
  estimated_saved_usd: string
  spend_granularity: 'day' | 'week' | 'month'
  spend: { start: string; cost_usd: string; emails: number }[]
  label_months: { label_id: string; name: string; color: LabelColor; this_month: number; last_month: number }[]
}

export type DashboardAttention = {
  labels_without_condition: LabelRef[]
  labels_stale: LabelRef[]
  labels_never_run: LabelRef[]
  labels_near_threshold: LabelRef[]
  labels_likely_misses: LabelRef[]
  near_window: number
  runs_with_problems: {
    run_id: string
    name: string
    status: string
    emails_failed: number
    error: string | null
    created_at: string
  }[]
  inboxes_with_errors: { inbox_id: string; name: string; email_address: string; error: string; run_id: string }[]
}

export type DashboardStatus = {
  inboxes: {
    inbox_id: string
    name: string
    email_address: string
    last_scanned_at: string | null
    scanned_since: string | null
    quota_used: number
    quota_limit: number
    quota_window_seconds: number
  }[]
}

export type DashboardCoverage = {
  span_start: string | null
  span_end: string
  labels: { label_id: string; name: string; color: LabelColor; covered: { start: string; end: string }[] }[]
}

export type DashboardRecent = {
  matches: {
    email_id: string
    sent_at: string
    from_address: string | null
    subject: string | null
    inbox_name: string
    label_id: string
    label_name: string
    color: LabelColor
    probability: number
    labelled_at: string
  }[]
}

const key = ['dashboard'] as const

export function useDashboardSummary(start: string | null, end: string | null) {
  const params = new URLSearchParams({ tz: timeZone })
  if (start) params.set('start', start)
  if (end) params.set('end', end)
  return useQuery({
    queryKey: [...key, 'summary', params.toString()],
    queryFn: () => apiFetch<DashboardSummary>(`/dashboard/summary?${params}`),
    placeholderData: keepPreviousData,
  })
}

export function useDashboardAttention() {
  return useQuery({ queryKey: [...key, 'attention'], queryFn: () => apiFetch<DashboardAttention>('/dashboard/attention') })
}

/** Live: quota use changes by the second during a run. */
export function useDashboardStatus(live: boolean) {
  return useQuery({
    queryKey: [...key, 'status'],
    queryFn: () => apiFetch<DashboardStatus>('/dashboard/status'),
    refetchInterval: live ? 3_000 : false,
  })
}

export function useDashboardCoverage() {
  return useQuery({ queryKey: [...key, 'coverage'], queryFn: () => apiFetch<DashboardCoverage>('/dashboard/coverage') })
}

export function useDashboardRecent() {
  return useQuery({ queryKey: [...key, 'recent'], queryFn: () => apiFetch<DashboardRecent>('/dashboard/recent?limit=8') })
}
