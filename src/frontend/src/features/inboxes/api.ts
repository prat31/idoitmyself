import { useMutation, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'
import type { ScanKind, ScanStatus } from '@/features/scans/api'

export type InboxProvider = 'gmail'

export type Tag = {
  id: string
  name: string
}

export type Inbox = {
  id: string
  provider: InboxProvider
  name: string
  email_address: string
  notes: string | null
  tags: Tag[]
  connected_at: string
  created_at: string
  /** Active filters whose scope covers this inbox (by its mailbox type or by name). */
  active_filters: number
  /** End of the last scheduled scan's window (null: never scanned on schedule). */
  scanned_until: string | null
  last_scan: {
    id: string
    kind: ScanKind
    status: ScanStatus
    error: string | null
    emails_found: number
    emails_processed: number
    created_at: string
    finished_at: string | null
  } | null
}

export type InboxDraft = {
  name: string
  tags: string[]
  notes: string | null
}

export const inboxKeys = {
  all: ['inboxes'] as const,
}

export const tagKeys = {
  all: ['tags'] as const,
}

export function useInboxes() {
  // Scan state changes on the server's schedule, so refresh now and then.
  return useQuery({
    queryKey: inboxKeys.all,
    queryFn: () => apiFetch<Inbox[]>('/email/inboxes'),
    refetchInterval: 30_000,
  })
}

export function useTags() {
  return useQuery({ queryKey: tagKeys.all, queryFn: () => apiFetch<Tag[]>('/tags') })
}

/** Starts Gmail OAuth: the backend stores the draft and returns Google's consent URL to navigate to. */
export function useStartGmailAuthorization() {
  return useMutation({
    mutationFn: (draft: InboxDraft) =>
      apiFetch<{ authorization_url: string }>('/email/gmail/authorize', {
        method: 'POST',
        body: JSON.stringify(draft),
      }),
    onSuccess: ({ authorization_url }) => {
      window.location.assign(authorization_url)
    },
  })
}
