import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { Dataset } from '@/features/dashboards/api'
import type { LabelColor } from '@/features/labels/colors'

export type ProcessorStatus = 'active' | 'inactive'

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'skipped' | 'failed' | 'needs_input' | 'cancelled'

/** A kind from the code (e.g. credit card statements): the datasets it writes. */
export type ProcessorKind = {
  key: string
  name: string
  description: string
  version: number
  writes: Dataset[]
  config_schema: Record<string, unknown> | null
  has_dashboard: boolean
}

export type ProcessorLabel = { id: string; display_name: string; color: LabelColor }

export type Processor = {
  id: string
  name: string
  description: string | null
  labels: ProcessorLabel[]
  kind: string
  kind_name: string
  config: Record<string, unknown>
  status: ProcessorStatus
  status_changed_at: string
  created_at: string
  runs: { active: number; succeeded: number; skipped: number; failed: number; needs_input: number }
  last_run_at: string | null
  /** Records it has written, in every dataset. */
  records: number
  has_dashboard: boolean
  /** A built-in default: editable and can be deactivated, but not deleted. */
  is_default: boolean
}

export type ProcessorRun = {
  id: string
  status: RunStatus
  error: string | null
  attempts: number
  records_written: number
  /** What a `needs_input` run waits for. */
  input_name: string | null
  input_scope: string | null
  input_prompt: string | null
  created_at: string
  finished_at: string | null
  email_id: string
  sent_at: string
  from_address: string | null
  subject: string | null
  inbox_name: string
  /** Opens the message in its provider's web UI (null if there's none). */
  open_url: string | null
}

export type RunPage = { items: ProcessorRun[]; total: number; page: number; page_size: number }

export const processorKeys = { all: ['processors'] as const }

export function useProcessorKinds() {
  return useQuery({
    queryKey: [...processorKeys.all, 'kinds'],
    queryFn: () => apiFetch<ProcessorKind[]>('/processors/kinds'),
    staleTime: Infinity,
  })
}

export function useProcessors() {
  return useQuery({ queryKey: processorKeys.all, queryFn: () => apiFetch<Processor[]>('/processors') })
}

/** Refreshes every few seconds while its runs are queued or running. */
export function useProcessor(id: string) {
  return useQuery({
    queryKey: [...processorKeys.all, id],
    queryFn: () => apiFetch<Processor>(`/processors/${id}`),
    refetchInterval: (query) => (query.state.data?.runs.active ? 5_000 : false),
  })
}

/** Runs that didn't produce a result: failed, skipped or waiting for a PDF password. */
export function useProcessorProblemRuns(id: string, refetchInterval?: number) {
  return useQuery({
    queryKey: [...processorKeys.all, id, 'runs', 'problems'],
    queryFn: () =>
      apiFetch<RunPage>(`/processors/${id}/runs?status=failed&status=needs_input&status=skipped&page_size=50`),
    refetchInterval,
  })
}

export type ProcessorDraft = { name: string; description: string | null; label_ids: string[]; kind: string }

export function useCreateProcessor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (draft: ProcessorDraft) =>
      apiFetch<Processor>('/processors', { method: 'POST', body: JSON.stringify(draft) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: processorKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}

/** The name, description, labels and status are editable; the kind isn't. */
export function useUpdateProcessor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      changes,
    }: {
      id: string
      changes: { name?: string; description?: string | null; label_ids?: string[]; status?: ProcessorStatus }
    }) => apiFetch<Processor>(`/processors/${id}`, { method: 'PATCH', body: JSON.stringify(changes) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: processorKeys.all }),
  })
}

export function useDeleteProcessor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/processors/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: processorKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}

/** Runs on labelled emails never run through it. Answers how many were queued. */
export function useRunExisting() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch<{ queued: number }>(`/processors/${id}/run-existing`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: processorKeys.all }),
  })
}

/** Runs the processor's failed or skipped runs again (e.g. after a parser was added); each replaces what
 *  it wrote before. */
export function useRerun(status: 'failed' | 'skipped') {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ queued: number }>(`/processors/${id}/rerun?status=${status}`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: processorKeys.all }),
  })
}

/** Saves something a processor asked for (e.g. a PDF password); the runs waiting for it run again. */
export function useSaveInput() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; scope: string; value: string }) =>
      apiFetch<{ queued: number }>('/processors/inputs', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: processorKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['home'] })
    },
  })
}
