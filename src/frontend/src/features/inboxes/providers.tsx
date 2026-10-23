import { Mail, type LucideIcon } from 'lucide-react'

import type { InboxProvider } from './api'

export type ProviderInfo = {
  id: InboxProvider
  label: string
  description: string
  icon: LucideIcon
}

/** Inbox providers the user can connect. Add new providers here. */
export const providers: ProviderInfo[] = [
  { id: 'gmail', label: 'Gmail', description: 'Google account · read-only access', icon: Mail },
]

export const providerById = Object.fromEntries(providers.map((p) => [p.id, p])) as Record<InboxProvider, ProviderInfo>
