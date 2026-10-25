import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import { inboxKeys, type InboxProvider } from '@/features/inboxes/api'
import { labelKeys } from '@/features/labels/api'

/** An inbox provider. A filter's scope can cover whole mailbox types and/or individual inboxes. */
export type MailboxType = InboxProvider
export type FilterStatus = 'active' | 'inactive'
/** How an item joins the one before it. AND binds tighter than OR. */
export type Join = 'and' | 'or'

export type Condition = {
  type: 'condition'
  /** Omitted on the first item of a list. */
  join?: Join
  field: string
  op: string
  /** Text: a string; number: a number; enum: an option, or options for "in"; omitted when the
   *  operator takes no value. */
  value?: string | number | string[]
  /** Extra input some fields need, e.g. the header name. */
  argument?: string
  case_sensitive?: boolean
}

/** Brackets: conditions with their own joins. */
export type SubGroup = { type: 'group'; join?: Join; items: Condition[] }

/** Conditions and groups (which hold conditions only), each joined to the one before it by AND / OR;
 *  AND binds tighter, so `A OR B AND C` is `A OR (B AND C)`. At most two levels. */
export type Rule = { type: 'group'; items: (Condition | SubGroup)[] }

export type Filter = {
  id: string
  name: string
  description: string | null
  /** Every inbox of `mailbox_types` (including ones connected later), plus `inboxes` chosen one by one. */
  scope: {
    mailbox_types: MailboxType[]
    inboxes: { id: string; name: string; email_address: string; provider: MailboxType }[]
  }
  label: { id: string; name: string; display_name: string; color: string }
  rule: Rule
  status: FilterStatus
  status_changed_at: string
  /** Emails this filter labelled. */
  emails_labelled: number
  last_matched_at: string | null
  created_at: string
  updated_at: string
}

export type FilterInput = {
  name: string
  description: string | null
  scope: { mailbox_types: MailboxType[]; inbox_ids: string[] }
  label_id: string
  rule: Rule
  status: FilterStatus
}

export type FieldType = 'text' | 'text_list' | 'bool' | 'number' | 'enum'

export type FieldSpec = {
  key: string
  label: string
  type: FieldType
  description: string
  /** null: every mailbox type. */
  mailbox_types: MailboxType[] | null
  options: { value: string; label: string }[]
  argument_label: string | null
}

export type OperatorSpec = { key: string; label: string; takes_value: boolean }

export type FieldCatalogue = {
  mailbox_types: MailboxType[]
  fields: FieldSpec[]
  operators: Record<FieldType, OperatorSpec[]>
}

export const filterKeys = {
  all: ['filters'] as const,
  catalogue: ['filters', 'fields'] as const,
}

export function useFilters() {
  return useQuery({ queryKey: filterKeys.all, queryFn: () => apiFetch<Filter[]>('/filters') })
}

export function useFilter(id: string | undefined) {
  return useQuery({
    queryKey: [...filterKeys.all, id],
    queryFn: () => apiFetch<Filter>(`/filters/${id}`),
    enabled: !!id,
  })
}

export function useFieldCatalogue() {
  return useQuery({
    queryKey: filterKeys.catalogue,
    queryFn: () => apiFetch<FieldCatalogue>('/filters/fields'),
    staleTime: Infinity, // defined in code; only changes with a deploy
  })
}

/** Filters show up in labels (who writes them) and inboxes (active filter counts). */
function useInvalidateFilterViews() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: filterKeys.all }),
      queryClient.invalidateQueries({ queryKey: labelKeys.all }),
      queryClient.invalidateQueries({ queryKey: inboxKeys.all }),
    ])
}

export function useCreateFilter() {
  const invalidate = useInvalidateFilterViews()
  return useMutation({
    mutationFn: (data: FilterInput) => apiFetch<Filter>('/filters', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: invalidate,
  })
}

export type FilterChanges = Partial<FilterInput>

export function useUpdateFilter() {
  const invalidate = useInvalidateFilterViews()
  return useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: FilterChanges }) =>
      apiFetch<Filter>(`/filters/${id}`, { method: 'PATCH', body: JSON.stringify(changes) }),
    onSuccess: invalidate,
  })
}

export function useDeleteFilter() {
  const invalidate = useInvalidateFilterViews()
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/filters/${id}`, { method: 'DELETE' }),
    onSuccess: invalidate,
  })
}
