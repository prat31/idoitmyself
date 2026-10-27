import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'

export type ScanStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type ScanKind = 'scheduled' | 'adhoc'

export type Scan = {
  id: string
  inbox_id: string
  inbox_name: string
  inbox_email_address: string
  /** scheduled: at each boundary of the scan interval, from where the inbox's last scheduled scan stopped;
   *  adhoc: chosen filters over a past range, requested from the Scans page. */
  kind: ScanKind
  status: ScanStatus
  /** Emails received in [window_start, window_end) are listed. */
  window_start: string | null
  window_end: string | null
  started_at: string | null
  discovered_at: string | null
  finished_at: string | null
  error: string | null
  emails_found: number
  emails_processed: number
  /** Of emails_processed: already stored by an earlier scan, so not fetched or filtered again. */
  emails_skipped: number
  emails_failed: number
  emails_matched: number
  labels_applied: number
  /** Emails re-queued with a delay after a transient failure (rate limit, 5xx, network). */
  retries: number
  /** Ad hoc scans: the filters they run. */
  filters: { id: string; name: string }[]
  created_at: string
  updated_at: string
}

export const scanKindLabel: Record<ScanKind, string> = { scheduled: 'Scheduled', adhoc: 'Ad hoc' }

export type ScanPage = { items: Scan[]; total: number; page: number; page_size: number }

export const scanKeys = {
  all: ['scans'] as const,
}

export const isActiveScan = (scan: Scan) => scan.status === 'queued' || scan.status === 'running'

/** One page of scans, newest first. Polls while any scan on the page is in flight. */
export function useScans(page: number, pageSize: number) {
  return useQuery({
    queryKey: [...scanKeys.all, 'page', page, pageSize],
    queryFn: () => apiFetch<ScanPage>(`/scans?page=${page}&page_size=${pageSize}`),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.items.some(isActiveScan) ? 3_000 : 30_000),
  })
}

/** Scans in flight. Scans are started by the server on a schedule, so this keeps polling slowly
 *  when idle to notice new ones, and quickly while any is running. */
export function useActiveScans() {
  return useQuery({
    queryKey: [...scanKeys.all, 'active'],
    queryFn: () => apiFetch<ScanPage>('/scans?active=true&page_size=100'),
    refetchInterval: (query) => (query.state.data?.total ? 3_000 : 30_000),
  })
}

export type AdhocScanInput = { filter_ids: string[]; window_start: string; window_end: string }

/** Queues one ad hoc scan per inbox the chosen filters cover; returns them. */
export function useCreateAdhocScans() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: AdhocScanInput) =>
      apiFetch<Scan[]>('/scans/adhoc', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: scanKeys.all }),
  })
}

/** Stops a queued or running scan; emails already stored and labels already added stay. */
export function useCancelScan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch<Scan>(`/scans/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: scanKeys.all }),
  })
}

/** Scheduled scans run every `interval_minutes` (one of `intervals`), counted from midnight in
 *  `timezone` (a server setting). */
export type ScanSchedule = { interval_minutes: number; intervals: number[]; timezone: string; next_run_at: string }

const scheduleKey = [...scanKeys.all, 'schedule'] as const

/** The scheduled-scan interval and the next tick. Refetched once that tick has passed. */
export function useScanSchedule() {
  return useQuery({
    queryKey: scheduleKey,
    queryFn: () => apiFetch<ScanSchedule>('/scans/schedule'),
    refetchInterval: (query) => {
      const next = query.state.data?.next_run_at
      return next ? Math.max(5_000, new Date(next).getTime() - Date.now() + 1_000) : 30_000
    },
  })
}

/** Changes how often scheduled scans run; applies from the next tick. */
export function useUpdateScanSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (intervalMinutes: number) =>
      apiFetch<ScanSchedule>('/scans/schedule', {
        method: 'PUT',
        body: JSON.stringify({ interval_minutes: intervalMinutes }),
      }),
    onSuccess: (schedule) => {
      queryClient.setQueryData(scheduleKey, schedule)
      return queryClient.invalidateQueries({ queryKey: ['dashboard', 'status'] })
    },
  })
}
