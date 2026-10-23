import { useMutation, useQuery } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'

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
  return useQuery({ queryKey: inboxKeys.all, queryFn: () => apiFetch<Inbox[]>('/email/inboxes') })
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
