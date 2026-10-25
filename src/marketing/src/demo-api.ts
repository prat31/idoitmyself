/* Static demo transport: real application components call their ordinary API client, but requests
 * are satisfied here with fictional data. Mutations deliberately fail, keeping every visible
 * create/edit/delete control present without allowing a visitor to change the demonstration. */

const now = new Date().toISOString()
const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString()
const dayStart = (daysAgo: number) => {
  const d = new Date(Date.now() - daysAgo * 86_400_000)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const labels = [
  { id: 'label-receipts', name: 'receipts', display_name: 'Receipts', color: 'amber', email_count: 742, filters: [{ id: 'filter-receipts', name: 'Invoice & receipt catcher', status: 'active' }], created_at: ago(90_000) },
  { id: 'label-projects', name: 'projects', display_name: 'Projects', color: 'blue', email_count: 488, filters: [{ id: 'filter-projects', name: 'Northstar project mail', status: 'active' }], created_at: ago(90_000) },
  { id: 'label-travel', name: 'travel', display_name: 'Travel', color: 'green', email_count: 337, filters: [{ id: 'filter-travel', name: 'Travel confirmations', status: 'active' }], created_at: ago(70_000) },
  { id: 'label-reading', name: 'reading_list', display_name: 'Reading list', color: 'violet', email_count: 279, filters: [], created_at: ago(60_000) },
]

const inboxes = [
  { id: 'inbox-work', provider: 'gmail', name: 'Work mailbox', email_address: 'finance@northstar.example', notes: 'Fictional demo mailbox', tags: [{ id: 'tag-work', name: 'Work' }], connected_at: ago(90_000), created_at: ago(90_000), active_filters: 2, scanned_until: ago(12), last_scan: { id: 'scan-work', kind: 'scheduled', status: 'completed', error: null, emails_found: 128, emails_processed: 128, created_at: ago(12), finished_at: ago(11) } },
  { id: 'inbox-personal', provider: 'gmail', name: 'Personal mailbox', email_address: 'me@example.test', notes: null, tags: [{ id: 'tag-personal', name: 'Personal' }], connected_at: ago(75_000), created_at: ago(75_000), active_filters: 3, scanned_until: ago(12), last_scan: { id: 'scan-personal', kind: 'scheduled', status: 'completed', error: null, emails_found: 64, emails_processed: 64, created_at: ago(12), finished_at: ago(11) } },
]

const rule = (field: string, op: string, value: string) => ({ type: 'group', items: [{ type: 'condition', field, op, value }] })
const filters = [
  { id: 'filter-receipts', name: 'Invoice & receipt catcher', description: 'Keep billing and purchase records easy to find.', scope: { mailbox_types: ['gmail'], inboxes: [] }, label: labels[0], rule: rule('subject', 'contains', 'invoice'), status: 'active', status_changed_at: ago(50_000), emails_labelled: 382, last_matched_at: ago(65), created_at: ago(80_000), updated_at: ago(65) },
  { id: 'filter-projects', name: 'Northstar project mail', description: 'Project discussions from the fictional Northstar team.', scope: { mailbox_types: [], inboxes: [inboxes[0]] }, label: labels[1], rule: rule('sender_domain', 'is', 'northstar.example'), status: 'active', status_changed_at: ago(45_000), emails_labelled: 261, last_matched_at: ago(120), created_at: ago(70_000), updated_at: ago(120) },
  { id: 'filter-travel', name: 'Travel confirmations', description: null, scope: { mailbox_types: ['gmail'], inboxes: [] }, label: labels[2], rule: rule('subject', 'matches_regex', 'booking|confirmation|itinerary'), status: 'active', status_changed_at: ago(30_000), emails_labelled: 194, last_matched_at: ago(2_800), created_at: ago(55_000), updated_at: ago(2_800) },
  { id: 'filter-reading', name: 'Newsletter reading list', description: 'A paused example rule.', scope: { mailbox_types: [], inboxes: [inboxes[1]] }, label: labels[3], rule: rule('is_from_mailing_list', 'is_true', ''), status: 'inactive', status_changed_at: ago(3_000), emails_labelled: 0, last_matched_at: null, created_at: ago(20_000), updated_at: ago(3_000) },
]

const scan = (id: string, inbox: (typeof inboxes)[number], kind: 'scheduled' | 'adhoc', minutes: number, found: number, matched: number) => ({ id, inbox_id: inbox.id, inbox_name: inbox.name, inbox_email_address: inbox.email_address, kind, status: 'completed', window_start: ago(minutes + 30), window_end: ago(minutes), started_at: ago(minutes + 1), discovered_at: ago(minutes + 1), finished_at: ago(minutes), error: null, emails_found: found, emails_processed: found, emails_skipped: 0, emails_failed: 0, emails_matched: matched, labels_applied: matched, retries: 0, filters: kind === 'adhoc' ? [{ id: filters[0].id, name: filters[0].name }] : [], created_at: ago(minutes + 2), updated_at: ago(minutes) })
const scans = [scan('scan-work', inboxes[0], 'scheduled', 12, 128, 22), scan('scan-personal', inboxes[1], 'scheduled', 12, 64, 11), scan('scan-adhoc', inboxes[0], 'adhoc', 1_440, 642, 108)]

const timeline = Array.from({ length: 30 }, (_, index) => ({
  start: dayStart(29 - index),
  emails: 220 + ((index * 37) % 140),
  labelled: 30 + ((index * 19) % 65),
}))
const emails = [
  { id: 'mail-1', inbox_id: inboxes[0].id, inbox_name: inboxes[0].name, sent_at: ago(65), from_address: 'billing@ledgerly.example', to_addresses: inboxes[0].email_address, subject: 'Your October invoice is ready', snippet: 'Your fictional invoice is attached to this preview message.', labels: [{ label_id: labels[0].id, display_name: labels[0].display_name, color: labels[0].color, filter_name: filters[0].name }], scanned_at: ago(60), open_url: null },
  { id: 'mail-2', inbox_id: inboxes[0].id, inbox_name: inboxes[0].name, sent_at: ago(120), from_address: 'team@northstar.example', to_addresses: inboxes[0].email_address, subject: 'Design review — sprint 24', snippet: 'Preview data only.', labels: [{ label_id: labels[1].id, display_name: labels[1].display_name, color: labels[1].color, filter_name: filters[1].name }], scanned_at: ago(115), open_url: null },
  { id: 'mail-3', inbox_id: inboxes[1].id, inbox_name: inboxes[1].name, sent_at: ago(2_800), from_address: 'confirm@waypoint.example', to_addresses: inboxes[1].email_address, subject: 'Travel confirmation: Bengaluru → Kochi', snippet: 'Preview data only.', labels: [{ label_id: labels[2].id, display_name: labels[2].display_name, color: labels[2].color, filter_name: filters[2].name }], scanned_at: ago(2_790), open_url: null },
]

const catalogue = {
  mailbox_types: ['gmail'],
  fields: [
    { key: 'sender_address', label: 'Sender address', type: 'text', description: 'Email address of the sender.', mailbox_types: null, options: [], argument_label: null },
    { key: 'sender_domain', label: 'Sender domain', type: 'text', description: 'Domain portion of the sender address.', mailbox_types: null, options: [], argument_label: null },
    { key: 'subject', label: 'Subject', type: 'text', description: 'Email subject line.', mailbox_types: null, options: [], argument_label: null },
    { key: 'has_attachments', label: 'Has attachments', type: 'bool', description: 'Whether the email has an attachment.', mailbox_types: null, options: [], argument_label: null },
    { key: 'is_from_mailing_list', label: 'Is from a mailing list', type: 'bool', description: 'Whether the email includes mailing-list headers.', mailbox_types: null, options: [], argument_label: null },
  ],
  operators: { text: [{ key: 'is', label: 'is', takes_value: true }, { key: 'contains', label: 'contains', takes_value: true }, { key: 'matches_regex', label: 'matches regex', takes_value: true }], text_list: [{ key: 'contains', label: 'contains', takes_value: true }], bool: [{ key: 'is_true', label: 'is true', takes_value: false }, { key: 'is_false', label: 'is false', takes_value: false }], number: [{ key: 'eq', label: '=', takes_value: true }], enum: [{ key: 'is', label: 'is', takes_value: true }] },
}

const overview = { window_start: ago(43_200), window_end: now, granularity: 'day', totals: { emails: 12_482, labelled_emails: 1_846, label_assignments: 1_913, senders: 1_102 }, timeline, by_label: labels.map((label) => ({ label_id: label.id, name: label.name, display_name: label.display_name, color: label.color, emails: label.email_count })), by_filter: filters.map((filter) => ({ filter_id: filter.id, name: filter.name, label_display_name: filter.label.display_name, emails: filter.emails_labelled })), by_inbox: inboxes.map((inbox, index) => ({ inbox_id: inbox.id, name: inbox.name, email_address: inbox.email_address, emails: index ? 5_098 : 7_384 })), top_senders: [{ sender: 'billing@ledgerly.example', emails: 142 }, { sender: 'team@northstar.example', emails: 118 }, { sender: 'updates@waypoint.example', emails: 74 }] }

function result(body: unknown, status = 200) { return new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }) }

export function installDemoApi() {
  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const url = new URL(typeof input === 'string' ? input : input instanceof Request ? input.url : input.toString(), window.location.origin)
    if (!url.pathname.startsWith('/api/v1/')) return originalFetch(input, init)
    const method = init?.method?.toUpperCase() ?? (input instanceof Request ? input.method : 'GET')
    if (method !== 'GET') return result({ detail: 'This is a read-only demo. Changes are disabled.' }, 403)
    const path = url.pathname.slice('/api/v1'.length)
    if (path === '/filters') return result(filters)
    if (path === '/filters/fields') return result(catalogue)
    if (path.startsWith('/filters/')) return result(filters.find((filter) => filter.id === path.split('/')[2]) ?? filters[0])
    if (path === '/labels') return result(labels)
    if (path.startsWith('/labels/')) {
      const [, , id, detail] = path.split('/')
      const label = labels.find((item) => item.id === id) ?? labels[0]
      if (detail === 'stats') return result({ label_id: label.id, granularity: 'day', emails: label.email_count, emails_last_30_days: Math.round(label.email_count / 3), first_sent_at: ago(40_000), last_sent_at: ago(65), timeline, by_filter: overview.by_filter, by_inbox: overview.by_inbox, top_senders: overview.top_senders })
      if (detail === 'emails') return result({ items: emails.map((email) => ({ ...email, filter_id: email.labels[0]?.label_id ?? null, filter_name: email.labels[0]?.filter_name ?? null, applied_at: email.scanned_at, other_labels: [] })), total: emails.length, page: 1, page_size: 25 })
      return result(label)
    }
    if (path === '/email/inboxes') return result(inboxes)
    if (path === '/tags') return result([{ id: 'tag-work', name: 'Work' }, { id: 'tag-personal', name: 'Personal' }])
    if (path === '/scans/schedule') return result({ interval_minutes: 30, next_run_at: new Date(Date.now() + 12 * 60_000).toISOString() })
    if (path === '/scans') return result({ items: url.searchParams.get('active') ? [] : scans, total: url.searchParams.get('active') ? 0 : scans.length, page: 1, page_size: 25 })
    if (path === '/stats/overview') return result(overview)
    if (path === '/dashboard/summary') return result({ scans_completed: 96, scans_failed: 0, emails_scanned: 12_482, emails_labelled: 1_846, active_filters: 3, inactive_filters: 1, label_months: labels.slice(0, 3).map((label, index) => ({ label_id: label.id, display_name: label.display_name, color: label.color, this_month: [142, 98, 41][index], last_month: [114, 87, 47][index] })) })
    if (path === '/dashboard/attention') return result({ inboxes_with_errors: [], scans_with_problems: [], inboxes_without_filters: [], filters_never_matched: [], labels_without_active_filter: [{ label_id: labels[3].id, display_name: labels[3].display_name, color: labels[3].color }] })
    if (path === '/dashboard/status') return result({ scan_interval_minutes: 30, inboxes: inboxes.map((inbox) => ({ inbox_id: inbox.id, name: inbox.name, email_address: inbox.email_address, provider: inbox.provider, scanned_until: inbox.scanned_until, last_completed_scan_at: inbox.last_scan?.finished_at ?? null, active_scan: null, quota_used: 0, quota_limit: 900, quota_window_seconds: 10 })) })
    if (path === '/dashboard/recent') return result({ matches: emails.map((email) => ({ email_id: email.id, sent_at: email.sent_at, from_address: email.from_address, subject: email.subject, inbox_name: email.inbox_name, label_id: email.labels[0].label_id, label_display_name: email.labels[0].display_name, label_color: email.labels[0].color, filter_name: email.labels[0].filter_name, applied_at: email.scanned_at, open_url: null })) })
    if (path === '/emails') return result({ items: emails, total: emails.length, page: 1, page_size: 25, stats: { emails: emails.length, labelled: emails.length, unlabelled: 0, senders: emails.length, inboxes: 2, first_sent_at: emails[2].sent_at, last_sent_at: emails[0].sent_at } })
    return result({ detail: `No demo fixture for ${path}` }, 404)
  }
}
