import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { InboxCount, SenderCount, TimelineBucket, Granularity } from '@/features/stats/api'
import { timeZone } from '@/features/stats/api'
import type { LabelColor } from './colors'

export type Label = {
  id: string
  name: string
  description: string | null
  color: LabelColor
  /** Plain-language rule for which emails belong here; the classification question for the model. */
  filter_condition: string | null
  /** Jev's P(yes) must reach this for a run to apply the label. */
  match_threshold: number
  /** Emails carrying this label, across all inboxes. */
  email_count: number
  created_at: string
}

export type LabelCreate = {
  name: string
  description: string | null
  color: LabelColor
  filter_condition: string | null
  match_threshold: number
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
    mutationFn: (data: LabelCreate) => apiFetch<Label>('/labels', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: labelKeys.all }),
  })
}

/** Editable fields of a label. The name is immutable (the API rejects it). */
export type LabelChanges = Partial<Pick<Label, 'description' | 'color' | 'filter_condition' | 'match_threshold'>>

export function useUpdateLabel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: LabelChanges }) =>
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
  avg_probability: number | null
  first_sent_at: string | null
  last_sent_at: string | null
  timeline: TimelineBucket[]
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
  probability: number
  run_id: string | null
  run_name: string | null
  other_labels: { label_id: string; name: string; color: LabelColor }[]
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
