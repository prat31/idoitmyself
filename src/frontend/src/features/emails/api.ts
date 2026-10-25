import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'

export type EmailSort = 'sent_desc' | 'sent_asc' | 'sender_asc' | 'sender_desc' | 'subject_asc' | 'subject_desc'

export type EmailRow = {
  id: string
  inbox_id: string
  inbox_name: string
  sent_at: string
  from_address: string | null
  to_addresses: string | null
  subject: string | null
  snippet: string | null
  /** Labels on the email, with the filter that added each (null if deleted since). */
  labels: { label_id: string; display_name: string; color: string; filter_name: string | null }[]
  scanned_at: string
  /** Opens the message in its provider's web UI (null if there's none). */
  open_url: string | null
}

export type EmailList = {
  items: EmailRow[]
  total: number
  page: number
  page_size: number
  /** Over every email matching the filters, not just this page. */
  stats: {
    emails: number
    labelled: number
    unlabelled: number
    senders: number
    inboxes: number
    first_sent_at: string | null
    last_sent_at: string | null
  }
}

export type EmailQuery = {
  start: string | null
  end: string | null
  inboxId: string | null
  labelIds: string[]
  /** true: labelled only; false: unlabelled only; null: both. */
  labelled: boolean | null
  q: string
  sort: EmailSort
  page: number
  pageSize: number
}

/** Stored emails (metadata only), filtered, searched, sorted and paged. */
export function useEmails(query: EmailQuery, refetchInterval?: number) {
  const params = new URLSearchParams({ sort: query.sort, page: String(query.page), page_size: String(query.pageSize) })
  if (query.start) params.set('start', query.start)
  if (query.end) params.set('end', query.end)
  if (query.inboxId) params.set('inbox_id', query.inboxId)
  query.labelIds.forEach((id) => params.append('label_id', id))
  if (query.labelled !== null) params.set('labelled', String(query.labelled))
  if (query.q.trim()) params.set('q', query.q.trim())
  return useQuery({
    queryKey: ['emails', params.toString()],
    queryFn: () => apiFetch<EmailList>(`/emails?${params}`),
    placeholderData: keepPreviousData,
    refetchInterval,
  })
}
