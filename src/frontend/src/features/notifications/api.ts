import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '@/lib/api'

export type Notification = {
  id: string
  title: string
  body: string | null
  created_at: string
  read_at: string | null
  processor_id: string | null
  processor_name: string | null
  /** Opens the email it's about in its provider's web UI (null if none). */
  open_url: string | null
}

export type NotificationPage = { items: Notification[]; total: number; unread: number; page: number; page_size: number }

const key = ['notifications'] as const

/** The latest notifications and the unread count; refreshed every 30 seconds. */
export function useNotifications(pageSize = 30) {
  return useQuery({
    queryKey: [...key, pageSize],
    queryFn: () => apiFetch<NotificationPage>(`/notifications?page_size=${pageSize}`),
    refetchInterval: 30_000,
  })
}

/** Marks one read or unread, updating the list at once (and undoing that if the request fails). */
export function useMarkRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, read }: { id: string; read: boolean }) =>
      apiFetch<void>(`/notifications/${id}/${read ? 'read' : 'unread'}`, { method: 'POST' }),
    onMutate: async ({ id, read }) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueriesData<NotificationPage>({ queryKey: key })
      queryClient.setQueriesData<NotificationPage>({ queryKey: key }, (page) => {
        if (!page) return page
        const target = page.items.find((n) => n.id === id)
        if (!target || !!target.read_at === read) return page
        return {
          ...page,
          unread: page.unread + (read ? -1 : 1),
          items: page.items.map((n) => (n.id === id ? { ...n, read_at: read ? new Date().toISOString() : null } : n)),
        }
      })
      return { previous }
    },
    onError: (_error, _vars, context) => context?.previous.forEach(([k, data]) => queryClient.setQueryData(k, data)),
    onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
  })
}

/** Removes one from the list at once (and puts it back if the request fails). */
export function useDismiss() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/notifications/${id}/dismiss`, { method: 'POST' }),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: key })
      const previous = queryClient.getQueriesData<NotificationPage>({ queryKey: key })
      queryClient.setQueriesData<NotificationPage>({ queryKey: key }, (page) => {
        const target = page?.items.find((n) => n.id === id)
        if (!page || !target) return page
        return {
          ...page,
          total: page.total - 1,
          unread: page.unread - (target.read_at ? 0 : 1),
          items: page.items.filter((n) => n.id !== id),
        }
      })
      return { previous }
    },
    onError: (_error, _id, context) => context?.previous.forEach(([k, data]) => queryClient.setQueryData(k, data)),
    onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
  })
}

export function useMarkAllRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>('/notifications/read-all', { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: key }),
  })
}
