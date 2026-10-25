import type { Inbox } from '@/features/inboxes/api'
import type { Filter, MailboxType } from './api'

/** What a filter applies to: whole mailbox types (every inbox of the type, including ones connected
 *  later) and/or individual inboxes. An inbox whose type is selected is never listed separately. */
export type ScopeDraft = { mailboxTypes: MailboxType[]; inboxIds: string[] }

export const scopeToDraft = (scope: Filter['scope']): ScopeDraft => ({
  mailboxTypes: scope.mailbox_types,
  inboxIds: scope.inboxes.map((i) => i.id),
})

/** Mailbox types the rule must suit: the selected types plus the types of selected inboxes. */
export function coveredTypes(scope: ScopeDraft, inboxes: Inbox[]): MailboxType[] {
  const types = new Set<MailboxType>(scope.mailboxTypes)
  for (const inbox of inboxes) if (scope.inboxIds.includes(inbox.id)) types.add(inbox.provider)
  return [...types]
}
