import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { LabelColor } from '@/features/labels/colors'
import { timeZone } from '@/features/stats/api'

export type RunStatus = 'queued' | 'running' | 'completed' | 'failed'

export type RunLabel = {
  label_id: string | null
  label_name: string
  filter_condition: string
  match_threshold: number
  matched: number
}

export type RunInbox = {
  inbox_id: string | null
  inbox_name: string
  email_address: string
  emails_found: number
  error: string | null
}

export type Run = {
  id: string
  name: string
  kind: 'adhoc'
  status: RunStatus
  window_start: string
  window_end: string
  model: string
  /** Re-asked the model even for emails already answered for a label. */
  reclassify: boolean
  created_at: string
  started_at: string | null
  finished_at: string | null
  error: string | null
  emails_found: number
  emails_processed: number
  /** Of emails_processed: every label already answered, so no fetch and no model call. */
  emails_skipped: number
  emails_failed: number
  emails_matched: number
  labels_applied: number
  labels_removed: number
  /** Emails re-queued with a delay after a transient failure (rate limit, 5xx, network). */
  retries: number
  cost_usd: string
  labels: RunLabel[]
  inboxes: RunInbox[]
}

export type AdhocRunCreate = {
  name: string
  label_ids: string[]
  inbox_ids: string[]
  window_start: string
  window_end: string
  reclassify: boolean
}

export type RunCoverage = {
  labels: {
    label_id: string
    label_name: string
    covered: { start: string; end: string }[]
    evaluated_emails: number
  }[]
}

/** Which parts of a prospective run's window were already scanned, per label. */
export function useRunCoverage(request: Omit<AdhocRunCreate, 'name' | 'reclassify'> | null) {
  return useQuery({
    queryKey: [...runKeys.all, 'coverage', request],
    queryFn: () => apiFetch<RunCoverage>('/runs/coverage', { method: 'POST', body: JSON.stringify(request) }),
    enabled: request !== null,
    placeholderData: keepPreviousData,
  })
}

export const runKeys = {
  all: ['runs'] as const,
}

const isActive = (run: Run) => run.status === 'queued' || run.status === 'running'

export function useRuns() {
  return useQuery({
    queryKey: runKeys.all,
    queryFn: () => apiFetch<Run[]>('/runs'),
    // Poll while any run is in flight so progress updates live.
    refetchInterval: (query) => (query.state.data?.some(isActive) ? 2_000 : false),
  })
}

export function useCreateAdhocRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AdhocRunCreate) =>
      apiFetch<Run>('/runs/adhoc', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runKeys.all })
      // Label email counts change as runs complete.
      queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}

export type RunLabelInsight = {
  label_id: string | null
  label_name: string
  color: LabelColor | null
  filter_condition: string
  match_threshold: number
  condition_changed: boolean
  asked: number
  matched: number
  near_threshold: number
  histogram: { start: number; count: number }[]
}

export type RunInsights = {
  near_window: number
  granularity: 'day' | 'week' | 'month'
  labels: RunLabelInsight[]
  matched_timeline: { start: string; emails: number }[]
}

export type RunEmailTab = 'matched' | 'near' | 'not_matched' | 'skipped'
export type RunEmailSort = 'probability_desc' | 'probability_asc' | 'sent_desc'

export type RunEmailRow = {
  email_id: string
  inbox_name: string
  sent_at: string
  from_address: string | null
  subject: string | null
  snippet: string | null
  result: {
    label_id: string | null
    label_name: string
    color: LabelColor | null
    probability: number
    matched: boolean
    from_this_run: boolean
  }
}

export type RunEmailPage = { items: RunEmailRow[]; total: number; page: number; page_size: number }

const isActiveRun = (run: Run | undefined) => run?.status === 'queued' || run?.status === 'running'

export function useRun(id: string) {
  return useQuery({
    queryKey: [...runKeys.all, id],
    queryFn: () => apiFetch<Run>(`/runs/${id}`),
    refetchInterval: (query) => (isActiveRun(query.state.data) ? 2_000 : false),
  })
}

export function useRunInsights(id: string, live: boolean) {
  return useQuery({
    queryKey: [...runKeys.all, id, 'insights'],
    queryFn: () => apiFetch<RunInsights>(`/runs/${id}/insights?tz=${encodeURIComponent(timeZone)}`),
    refetchInterval: live ? 5_000 : false,
  })
}

export function useRunEmails(
  id: string,
  params: { tab: RunEmailTab; labelId: string | null; sort: RunEmailSort; page: number; pageSize: number },
) {
  const search = new URLSearchParams({
    tab: params.tab,
    sort: params.sort,
    page: String(params.page),
    page_size: String(params.pageSize),
  })
  if (params.labelId) search.set('label_id', params.labelId)
  return useQuery({
    queryKey: [...runKeys.all, id, 'emails', search.toString()],
    queryFn: () => apiFetch<RunEmailPage>(`/runs/${id}/emails?${search}`),
    placeholderData: keepPreviousData,
  })
}
