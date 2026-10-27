import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { FilterCount, InboxCount, SenderCount, TimelineBucket, Granularity } from '@/features/stats/api'
import { timeZone } from '@/features/stats/api'
import type { LabelColor } from './colors'

export type LabelFilterRef = { id: string; name: string; status: 'active' | 'inactive' }

export type Label = {
  id: string
  /** Normalised name (lowercase snake case): unique and immutable. */
  name: string
  /** What the UI shows; editable. */
  display_name: string
  /** From the fixed palette; shown as a dot beside the name. Editable. */
  color: LabelColor
  /** Emails carrying this label, across all inboxes. */
  email_count: number
  /** Filters that write this label. A label can only be deleted when there are none. */
  filters: LabelFilterRef[]
  /** Processors that run on this label; they block deleting it too. */
  processors: LabelFilterRef[]
  /** A built-in default: editable, but it can't be deleted. */
  is_default: boolean
  created_at: string
}

export const labelKeys = {
  all: ['labels'] as const,
}

export function useLabels() {
  return useQuery({ queryKey: labelKeys.all, queryFn: () => apiFetch<Label[]>('/labels') })
}

export function useCreateLabel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ displayName, color }: { displayName: string; color: LabelColor }) =>
      apiFetch<Label>('/labels', { method: 'POST', body: JSON.stringify({ display_name: displayName, color }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: labelKeys.all }),
  })
}

/** The display name and colour are editable; the normalised name isn't. */
export function useUpdateLabel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: { display_name?: string; color?: LabelColor } }) =>
      apiFetch<Label>(`/labels/${id}`, { method: 'PATCH', body: JSON.stringify(changes) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: labelKeys.all }),
  })
}

export function useDeleteLabel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/labels/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: labelKeys.all }),
  })
}

export type LabelStats = {
  label_id: string
  granularity: Granularity
  emails: number
  emails_last_30_days: number
  first_sent_at: string | null
  last_sent_at: string | null
  timeline: TimelineBucket[]
  by_filter: FilterCount[]
  by_inbox: InboxCount[]
  top_senders: SenderCount[]
}

export type LabelledEmail = {
  id: string
  inbox_id: string
  inbox_name: string
  sent_at: string
  from_address: string | null
  subject: string | null
  snippet: string | null
  /** The filter that added the label (null if it was deleted since). */
  filter_id: string | null
  filter_name: string | null
  applied_at: string
  /** Opens the message in its provider's web UI (null if there's none). */
  open_url: string | null
  other_labels: { label_id: string; display_name: string; color: LabelColor }[]
}

export type EmailPage = { items: LabelledEmail[]; total: number; page: number; page_size: number }

export function useLabel(id: string) {
  return useQuery({ queryKey: [...labelKeys.all, id], queryFn: () => apiFetch<Label>(`/labels/${id}`) })
}

export function useLabelStats(id: string) {
  return useQuery({
    queryKey: [...labelKeys.all, id, 'stats'],
    queryFn: () => apiFetch<LabelStats>(`/labels/${id}/stats?tz=${encodeURIComponent(timeZone)}`),
  })
}

export function useLabelEmails(id: string, page: number, pageSize: number) {
  return useQuery({
    queryKey: [...labelKeys.all, id, 'emails', page, pageSize],
    queryFn: () => apiFetch<EmailPage>(`/labels/${id}/emails?page=${page}&page_size=${pageSize}`),
    placeholderData: keepPreviousData,
  })
}
