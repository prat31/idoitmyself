/* Static demo transport: real application components call their ordinary API client, but requests
 * are satisfied here with fictional data. Mutations deliberately fail, keeping every visible
 * create/edit/delete control present without allowing a visitor to change the demonstration. The two
 * dataset reads are POSTs by design and are answered from the same fictional records. */

const now = new Date().toISOString()
const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString()
const dayStart = (daysAgo: number) => {
  const d = new Date(Date.now() - daysAgo * 86_400_000)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}
const monthKey = (monthsAgo: number) => {
  const d = new Date()
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - monthsAgo, 1)).toISOString().slice(0, 10)
}
const monthKeys = Array.from({ length: 12 }, (_, index) => monthKey(11 - index))
const at = (date: string) => `${date}T00:00:00`
const shortDate = (date: string) => date.slice(0, 10)

type SeriesRow = { bucket: string | null; group: string | null; value: number | null }
type QueryBody = {
  dataset: string
  measure: string | null
  agg: string
  group_by: string | null
  bucket: string | null
  filters: { field: string; op?: string; values: string[] }[]
  limit: number | null
  start: string | null
  end: string | null
  processor_ids: string[]
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------------------------
// Labels, inboxes and filters

const labelCreditCard = {
  id: 'label-credit-card',
  name: 'credit_card_bill',
  display_name: 'Credit card bill',
  color: 'orange',
  email_count: 68,
  filters: [{ id: 'filter-bills', name: 'All Banks Credit Card Bills', status: 'active' }],
  processors: [{ id: 'processor-cards', name: 'Credit card bills', status: 'active' }],
  is_default: true,
  created_at: ago(90_000),
}
const labelReceipts = {
  id: 'label-receipts',
  name: 'receipts',
  display_name: 'Receipts',
  color: 'amber',
  email_count: 742,
  filters: [
    { id: 'filter-receipts', name: 'Invoice & receipt catcher', status: 'active' },
    { id: 'filter-ai-receipts', name: 'Receipts I might need', status: 'active' },
  ],
  processors: [],
  is_default: false,
  created_at: ago(90_000),
}
const labelProjects = {
  id: 'label-projects',
  name: 'projects',
  display_name: 'Projects',
  color: 'blue',
  email_count: 488,
  filters: [{ id: 'filter-projects', name: 'Northstar project mail', status: 'active' }],
  processors: [],
  is_default: false,
  created_at: ago(90_000),
}
const labelTravel = {
  id: 'label-travel',
  name: 'travel',
  display_name: 'Travel',
  color: 'green',
  email_count: 337,
  filters: [{ id: 'filter-travel', name: 'Travel confirmations', status: 'active' }],
  processors: [],
  is_default: false,
  created_at: ago(70_000),
}
const labelReading = {
  id: 'label-reading',
  name: 'reading_list',
  display_name: 'Reading list',
  color: 'violet',
  email_count: 279,
  filters: [],
  processors: [],
  is_default: false,
  created_at: ago(60_000),
}
const labels = [labelCreditCard, labelReceipts, labelProjects, labelTravel, labelReading]

const inboxWork = {
  id: 'inbox-work',
  provider: 'gmail',
  name: 'Work mailbox',
  email_address: 'finance@northstar.example',
  notes: 'Fictional demo mailbox',
  tags: [{ id: 'tag-work', name: 'Work' }],
  connected_at: ago(90_000),
  created_at: ago(90_000),
  active_filters: 2,
  scanned_until: ago(45),
  last_scan: {
    id: 'scan-work',
    kind: 'scheduled',
    status: 'completed',
    error: null,
    emails_found: 128,
    emails_processed: 128,
    created_at: ago(60),
    finished_at: ago(58),
  },
}
const inboxPersonal = {
  id: 'inbox-personal',
  provider: 'gmail',
  name: 'Personal mailbox',
  email_address: 'me@example.test',
  notes: null,
  tags: [{ id: 'tag-personal', name: 'Personal' }],
  connected_at: ago(75_000),
  created_at: ago(75_000),
  active_filters: 3,
  scanned_until: ago(45),
  last_scan: {
    id: 'scan-personal',
    kind: 'scheduled',
    status: 'running',
    error: null,
    emails_found: 84,
    emails_processed: 41,
    created_at: ago(4),
    finished_at: null,
  },
}
const inboxes = [inboxWork, inboxPersonal]

const condition = (field: string, op: string, value?: string, join?: 'and' | 'or') => ({
  type: 'condition' as const,
  ...(join ? { join } : {}),
  field,
  op,
  ...(value === undefined ? {} : { value }),
})
const group = (items: unknown[], join?: 'and' | 'or') => ({
  type: 'group' as const,
  ...(join ? { join } : {}),
  items,
})
const scopeInbox = (inbox: typeof inboxWork) => ({
  id: inbox.id,
  name: inbox.name,
  email_address: inbox.email_address,
  provider: inbox.provider,
})

const filters = [
  {
    id: 'filter-bills',
    name: 'All Banks Credit Card Bills',
    description: 'Credit card statements from the fictional demo banks.',
    scope: { mailbox_types: ['gmail'], inboxes: [] },
    label: labelCreditCard,
    rule: group([
      group([
        condition('from_address', 'equals', 'cards@hoolibank.example'),
        condition('from_address', 'equals', 'cards@initechbank.example', 'or'),
        condition('from_address', 'equals', 'statements@acmebank.example', 'or'),
        condition('from_address', 'equals', 'statements@globexbank.example', 'or'),
      ]),
      condition('has_attachments', 'is_true', undefined, 'and'),
      condition('from_address', 'ends_with', 'bank.example', 'and'),
    ]),
    status: 'active',
    status_changed_at: ago(50_000),
    emails_labelled: 68,
    last_matched_at: ago(35),
    is_default: true,
    created_at: ago(80_000),
    updated_at: ago(35),
  },
  {
    id: 'filter-receipts',
    name: 'Invoice & receipt catcher',
    description: 'Keep billing and purchase records easy to find.',
    scope: { mailbox_types: ['gmail'], inboxes: [] },
    label: labelReceipts,
    rule: group([condition('subject', 'contains', 'invoice')]),
    status: 'active',
    status_changed_at: ago(50_000),
    emails_labelled: 382,
    last_matched_at: ago(65),
    is_default: false,
    created_at: ago(80_000),
    updated_at: ago(65),
  },
  {
    id: 'filter-ai-receipts',
    name: 'Receipts I might need',
    description: 'A plain-English condition, decided by Jev.',
    scope: { mailbox_types: ['gmail'], inboxes: [] },
    label: labelReceipts,
    rule: group([
      condition(
        'ai',
        'matches',
        'A receipt or invoice for something I bought, not a newsletter or a promotion',
      ),
    ]),
    status: 'active',
    status_changed_at: ago(40_000),
    emails_labelled: 91,
    last_matched_at: ago(180),
    is_default: false,
    created_at: ago(60_000),
    updated_at: ago(180),
  },
  {
    id: 'filter-projects',
    name: 'Northstar project mail',
    description: 'Project discussions from the fictional Northstar team.',
    scope: { mailbox_types: [], inboxes: [scopeInbox(inboxWork)] },
    label: labelProjects,
    rule: group([condition('from_domain', 'equals', 'northstar.example')]),
    status: 'active',
    status_changed_at: ago(45_000),
    emails_labelled: 261,
    last_matched_at: ago(120),
    is_default: false,
    created_at: ago(70_000),
    updated_at: ago(120),
  },
  {
    id: 'filter-travel',
    name: 'Travel confirmations',
    description: null,
    scope: { mailbox_types: ['gmail'], inboxes: [] },
    label: labelTravel,
    rule: group([condition('subject', 'matches_regex', 'booking|confirmation|itinerary')]),
    status: 'active',
    status_changed_at: ago(30_000),
    emails_labelled: 194,
    last_matched_at: ago(2_800),
    is_default: false,
    created_at: ago(55_000),
    updated_at: ago(2_800),
  },
  {
    id: 'filter-reading',
    name: 'Newsletter reading list',
    description: 'A paused example rule.',
    scope: { mailbox_types: [], inboxes: [scopeInbox(inboxPersonal)] },
    label: labelReading,
    rule: group([condition('is_mailing_list', 'is_true')]),
    status: 'inactive',
    status_changed_at: ago(3_000),
    emails_labelled: 0,
    last_matched_at: null,
    is_default: false,
    created_at: ago(20_000),
    updated_at: ago(3_000),
  },
]

// ---------------------------------------------------------------------------------------------
// Processors, their runs, datasets and dashboard

const processor = {
  id: 'processor-cards',
  name: 'Credit card bills',
  description: 'Reads the statement PDF of every credit card bill: dues, fees and transactions.',
  labels: [{ id: labelCreditCard.id, display_name: labelCreditCard.display_name, color: labelCreditCard.color }],
  kind: 'credit_card_statements',
  kind_name: 'Credit card statements',
  config: {},
  status: 'active',
  status_changed_at: ago(80_000),
  created_at: ago(80_000),
  runs: { active: 0, succeeded: 34, skipped: 3, failed: 1, needs_input: 1 },
  last_run_at: ago(35),
  records: 118,
  has_dashboard: true,
  is_default: true,
}

const processorRuns = [
  {
    id: 'run-needs-input',
    status: 'needs_input',
    error: "PDF password for statements@globexbank.example (Credit card bill) (the saved one didn't work)",
    attempts: 1,
    records_written: 0,
    input_name: 'pdf_password',
    input_scope: 'statements@globexbank.example|credit_card_bill',
    input_prompt: 'PDF password for statements@globexbank.example (Credit card bill)',
    created_at: ago(120),
    finished_at: null,
    email_id: 'mail-globex',
    sent_at: ago(2_880),
    from_address: 'statements@globexbank.example',
    subject: 'Globex Bank credit card statement',
    inbox_name: inboxPersonal.name,
    open_url: null,
  },
  {
    id: 'run-failed',
    status: 'failed',
    error: 'The PDF has no text (it may be a scanned image)',
    attempts: 1,
    records_written: 0,
    input_name: null,
    input_scope: null,
    input_prompt: null,
    created_at: ago(320),
    finished_at: ago(318),
    email_id: 'mail-initech',
    sent_at: ago(3_600),
    from_address: 'cards@initechbank.example',
    subject: 'Your Initech Bank card statement ending XX76 - July 2026',
    inbox_name: inboxWork.name,
    open_url: null,
  },
  {
    id: 'run-skipped',
    status: 'skipped',
    error: 'No statement parser for umbrellabank.example',
    attempts: 1,
    records_written: 0,
    input_name: null,
    input_scope: null,
    input_prompt: null,
    created_at: ago(520),
    finished_at: ago(518),
    email_id: 'mail-umbrella',
    sent_at: ago(5_800),
    from_address: 'statements@umbrellabank.example',
    subject: 'Your Umbrella Bank credit card statement',
    inbox_name: inboxWork.name,
    open_url: null,
  },
]

const field = (
  name: string,
  title: string,
  type: string,
  role: string,
  description: string | null = null,
) => ({ name, title, type, role, description })

const datasets = [
  {
    name: 'cards.statements',
    title: 'Card statements',
    kind: 'event',
    time_field: 'statement_date',
    key_field: null,
    fields: [
      field('bank', 'Bank', 'text', 'dimension'),
      field('card', 'Card', 'text', 'dimension', 'Bank and last four digits, e.g. Acme Bank ••1234'),
      field('statement_date', 'Statement date', 'date', 'time'),
      field('period_start', 'Period from', 'date', 'time'),
      field('period_end', 'Period to', 'date', 'time'),
      field('due_date', 'Due date', 'date', 'time'),
      field('total_due', 'Total due', 'money', 'measure'),
      field('minimum_due', 'Minimum due', 'money', 'measure'),
      field('previous_balance', 'Previous balance', 'money', 'measure'),
      field('purchases_and_charges', 'Purchases & charges', 'money', 'measure'),
      field('payments_and_credits', 'Payments & credits', 'money', 'measure'),
      field('credit_limit', 'Credit limit', 'money', 'measure'),
      field('available_credit', 'Available credit', 'money', 'measure'),
      field('fees', 'Fees & charges', 'money', 'measure'),
      field('currency', 'Currency', 'text', 'dimension'),
    ],
  },
  {
    name: 'cards.transactions',
    title: 'Card transactions',
    kind: 'event',
    time_field: 'date',
    key_field: null,
    fields: [
      field('bank', 'Bank', 'text', 'dimension'),
      field('card', 'Card', 'text', 'dimension'),
      field('date', 'Date', 'date', 'time'),
      field('description', 'Description', 'text', 'text'),
      field('category', 'Category', 'text', 'dimension', "The bank's merchant category"),
      field('kind', 'Kind', 'text', 'dimension'),
      field('direction', 'Debit / credit', 'text', 'dimension'),
      field('amount', 'Amount', 'money', 'measure'),
      field('currency', 'Currency', 'text', 'dimension'),
    ],
  },
]

const kinds = [
  {
    key: 'credit_card_statements',
    name: 'Credit card statements',
    description: 'Reads statement PDFs: dues, limits, fees and every transaction. Reminds before the due date.',
    version: 3,
    writes: datasets,
    config_schema: null,
    has_dashboard: true,
  },
]

const query = (
  dataset: string,
  measure: string | null,
  agg: string,
  extra: Partial<QueryBody> = {},
): QueryBody => ({
  dataset,
  measure,
  agg,
  group_by: null,
  bucket: null,
  filters: [],
  limit: null,
  start: null,
  end: null,
  processor_ids: ['processor-cards'],
  ...extra,
})

const dashboardSpec = {
  default_range: '12m',
  widgets: [
    {
      id: 'total-due',
      type: 'stat',
      title: 'Total due',
      description: "Sum of the statements' total due",
      width: 'third',
      query: query('cards.statements', 'total_due', 'sum'),
    },
    {
      id: 'spend',
      type: 'stat',
      title: 'Card spend',
      description: 'Purchases and EMIs',
      width: 'third',
      query: query('cards.transactions', 'amount', 'sum', {
        filters: [{ field: 'kind', values: ['purchase', 'emi'] }],
      }),
    },
    {
      id: 'fees',
      type: 'stat',
      title: 'Fees & charges',
      description: 'Interest, fees and GST on them',
      width: 'third',
      query: query('cards.statements', 'fees', 'sum'),
    },
    {
      id: 'due-by-month',
      type: 'composition',
      title: 'Total due by month',
      description: 'By statement date, per card',
      width: 'full',
      query: query('cards.statements', 'total_due', 'sum', { bucket: 'month', group_by: 'card' }),
    },
    {
      id: 'spend-by-kind',
      type: 'composition',
      title: 'Spend by kind',
      description: 'Debits per month: purchases, EMIs and fees',
      width: 'half',
      query: query('cards.transactions', 'amount', 'sum', {
        bucket: 'month',
        group_by: 'kind',
        filters: [{ field: 'direction', values: ['debit'] }],
      }),
    },
    {
      id: 'spend-by-category',
      type: 'breakdown',
      title: 'Spend by category',
      description: "The bank's merchant categories",
      width: 'half',
      query: query('cards.transactions', 'amount', 'sum', {
        group_by: 'category',
        limit: 8,
        filters: [{ field: 'kind', values: ['purchase'] }],
      }),
    },
    {
      id: 'top-merchants',
      type: 'breakdown',
      title: 'Top merchants',
      width: 'half',
      query: query('cards.transactions', 'amount', 'sum', {
        group_by: 'description',
        limit: 10,
        filters: [{ field: 'kind', values: ['purchase'] }],
      }),
    },
    {
      id: 'due-by-card',
      type: 'breakdown',
      title: 'Total due by card',
      width: 'half',
      query: query('cards.statements', 'total_due', 'sum', { group_by: 'card' }),
    },
    {
      id: 'statements',
      type: 'table',
      title: 'Statements',
      width: 'full',
      query: query('cards.statements', null, 'count', {
        columns: [
          'statement_date',
          'card',
          'due_date',
          'total_due',
          'minimum_due',
          'fees',
          'available_credit',
        ],
      }),
    },
  ],
}

const dashboards = [
  {
    id: processor.id,
    name: 'Credit card bills',
    description: 'What the Credit card bills processor found in your email.',
    processor_status: 'active',
    kind: processor.kind,
    kind_name: processor.kind_name,
    labels: processor.labels,
    spec: dashboardSpec,
  },
]

const cards = [
  {
    card: 'Hooli Bank ••1234',
    bank: 'Hooli Bank',
    dues: [6842, 9210, 11240, 8730, 10670, 12180, 9640, 11840, 10230, 13210, 10980, 12345.67],
    fees: [0, 120, 0, 45, 0, 0, 180, 0, 0, 0, 0, 0],
    limit: 200000,
  },
  {
    card: 'Initech Bank ••5678',
    bank: 'Initech Bank',
    dues: [15420, 13880, 16110, 9270, 17430, 14900, 13240, 16870, 14560, 18120, 15980, 17240],
    fees: [240, 0, 0, 0, 310, 0, 0, 0, 150, 0, 0, 0],
    limit: 150000,
  },
]

const transactionKinds = [
  { kind: 'purchase', values: [7200, 8100, 9400, 6800, 10200, 11100, 8600, 10400, 9200, 11800, 9800, 10600] },
  { kind: 'emi', values: [0, 0, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200] },
  { kind: 'fee', values: [120, 0, 240, 0, 0, 310, 0, 0, 180, 0, 0, 0] },
]

const categories: [string, number][] = [
  ['Groceries', 28400],
  ['Travel', 22150],
  ['Shopping', 19640],
  ['Dining', 12800],
  ['Utilities', 9400],
  ['Fuel', 7100],
  ['Entertainment', 5400],
  ['Health', 3200],
]

const merchants: [string, number][] = [
  ['STYLEHOUSE FASHIONS', 12840],
  ['TRIPWISE TRAVEL', 9148],
  ['FRESHCART GROCERY', 7840],
  ['PAYWALLET TOPUP', 6120],
  ['QUICKBITE FOOD', 5480],
  ['MEGAMART ONLINE', 4930],
  ['RIDENOW CABS', 3420],
  ['SKYTEL PREPAID', 2980],
  ['GADGETZONE STORE', 2640],
  ['TASTYGO', 2210],
]

const round = (value: number) => Math.round(value * 100) / 100
const sum = (values: number[]) => values.reduce((total, value) => total + value, 0)
const inRange = (key: string, body: QueryBody) => {
  const start = body.start?.slice(0, 7)
  const end = body.end?.slice(0, 7)
  return (!start || key >= start) && (!end || key <= end)
}
const monthCount = (start: string, end: string) => {
  const [startYear, startMonth] = start.slice(0, 7).split('-').map(Number)
  const [endYear, endMonth] = end.slice(0, 7).split('-').map(Number)
  return Math.max(1, (endYear - startYear) * 12 + (endMonth - startMonth))
}
const recentStart = (body: QueryBody) =>
  Math.max(0, monthKeys.length - (body.start && body.end ? monthCount(body.start, body.end) : monthKeys.length))

function seriesRows(body: QueryBody): SeriesRow[] {
  // "vs previous period" asks for the range before the current one; keep the shape and scale it.
  const previous = body.end !== null
  const multiplier = previous ? 0.86 : 1

  if (body.dataset === 'cards.statements') {
    const measure = body.measure === 'fees' ? 'fees' : 'dues'
    if (body.bucket && body.group_by === 'card') {
      const rows: SeriesRow[] = []
      for (const card of cards) {
        monthKeys.forEach((key, index) => {
          if (inRange(key, body)) rows.push({ bucket: at(key), group: card.card, value: card[measure][index] })
        })
      }
      return rows
    }
    if (body.group_by === 'card') {
      return cards.map((card) => ({
        bucket: null,
        group: card.card,
        value: round(
          sum(monthKeys.map((key, index) => (inRange(key, body) ? card[measure][index] : 0))) * multiplier,
        ),
      }))
    }
    const value = previous
      ? sum(cards.flatMap((card) => card[measure].slice(recentStart(body)))) * multiplier
      : sum(
          cards.flatMap((card) =>
            monthKeys.map((key, index) => (inRange(key, body) ? card[measure][index] : 0)),
          ),
        )
    return [{ bucket: null, group: null, value: round(value) }]
  }

  if (body.dataset === 'cards.transactions') {
    const activeKinds = queryKinds(body)
    if (body.bucket && body.group_by === 'kind') {
      const rows: SeriesRow[] = []
      for (const kind of activeKinds) {
        monthKeys.forEach((key, index) => {
          if (inRange(key, body)) rows.push({ bucket: at(key), group: kind.kind, value: kind.values[index] })
        })
      }
      return rows
    }
    if (body.group_by === 'category') {
      return categories
        .slice(0, body.limit ?? categories.length)
        .map(([group, value]) => ({ bucket: null, group, value }))
    }
    if (body.group_by === 'description') {
      return merchants
        .slice(0, body.limit ?? merchants.length)
        .map(([group, value]) => ({ bucket: null, group, value }))
    }
    const value = previous
      ? sum(activeKinds.flatMap((kind) => kind.values.slice(recentStart(body)))) * multiplier
      : sum(
          activeKinds.flatMap((kind) =>
            monthKeys.map((key, index) => (inRange(key, body) ? kind.values[index] : 0)),
          ),
        )
    return [{ bucket: null, group: null, value: round(value) }]
  }

  return []
}

function queryKinds(body: QueryBody) {
  const wanted = body.filters?.find((filter) => filter.field === 'kind')?.values
  return wanted?.length ? transactionKinds.filter((kind) => wanted.includes(kind.kind)) : transactionKinds
}

function statementRecords() {
  return cards
    .flatMap((card, cardIndex) =>
      monthKeys.map((key, index) => {
        const date = new Date(`${key}T00:00:00Z`)
        const due = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 13))
        const start = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() - 1, 24))
        const dueDate = shortDate(due.toISOString())
        const total = card.dues[index]
        return {
          id: `statement-${cardIndex}-${key}`,
          occurred_at: at(key),
          processor_id: processor.id,
          data: {
            bank: card.bank,
            card: card.card,
            statement_date: key,
            period_start: shortDate(start.toISOString()),
            period_end: key,
            due_date: dueDate,
            total_due: total.toFixed(2),
            minimum_due: (total * 0.05).toFixed(2),
            previous_balance: (total * 0.12).toFixed(2),
            purchases_and_charges: (total * 0.94).toFixed(2),
            payments_and_credits: (total * 0.06).toFixed(2),
            credit_limit: card.limit.toFixed(2),
            available_credit: (card.limit - total).toFixed(2),
            fees: card.fees[index].toFixed(2),
            currency: 'INR',
          },
          email: {
            id: `mail-statement-${cardIndex}-${index}`,
            subject: `Your ${card.bank} credit card statement`,
            sent_at: `${key}T09:30:00`,
            open_url: null,
          },
        }
      }),
    )
    .sort((a, b) => (a.data.statement_date < b.data.statement_date ? 1 : -1))
}

function recordRows(body: QueryBody) {
  const start = body.start?.slice(0, 7)
  const end = body.end?.slice(0, 7)
  const filtered = statementRecords().filter(
    (row) =>
      (!start || row.data.statement_date.slice(0, 7) >= start) &&
      (!end || row.data.statement_date.slice(0, 7) <= end),
  )
  const page = body.page ?? 1
  const pageSize = body.page_size ?? 10
  return {
    items: filtered.slice((page - 1) * pageSize, page * pageSize),
    total: filtered.length,
    page,
    page_size: pageSize,
  }
}

// ---------------------------------------------------------------------------------------------
// Filter catalogue

const fieldSpec = (
  key: string,
  label: string,
  type: string,
  description: string,
  mailbox_types: string[] | null = null,
  options: { value: string; label: string }[] = [],
  argument_label: string | null = null,
) => ({ key, label, type, description, mailbox_types, options, argument_label })

const catalogue = {
  mailbox_types: ['gmail'],
  fields: [
    fieldSpec('from_address', 'Sender address', 'text', 'Email address in From'),
    fieldSpec('from_name', 'Sender name', 'text', 'Display name in From'),
    fieldSpec('from_domain', 'Sender domain', 'text', 'Domain of the From address'),
    fieldSpec('to', 'To', 'text_list', 'Any address in To'),
    fieldSpec('cc', 'Cc', 'text_list', 'Any address in Cc'),
    fieldSpec('any_recipient', 'Any recipient', 'text_list', 'Any address in To, Cc, Bcc or Delivered-To'),
    fieldSpec('reply_to', 'Reply-To', 'text_list', 'Any address in Reply-To'),
    fieldSpec('subject', 'Subject', 'text', 'Subject line'),
    fieldSpec('body', 'Body', 'text', 'Plain-text body (never stored)'),
    fieldSpec('has_attachments', 'Has attachments', 'bool', "At least one attached file (inline images don't count)"),
    fieldSpec('attachment_name', 'Attachment name', 'text_list', 'File name of any attachment'),
    fieldSpec('attachment_type', 'Attachment type', 'text_list', 'MIME type of any attachment, e.g. application/pdf'),
    fieldSpec('attachment_count', 'Attachment count', 'number', 'Number of attachments'),
    fieldSpec('size_bytes', 'Size (bytes)', 'number', 'Size of the whole message'),
    fieldSpec('is_reply', 'Is a reply', 'bool', 'Has In-Reply-To or References headers'),
    fieldSpec('is_mailing_list', 'Is from a mailing list', 'bool', 'Has List-Id or List-Unsubscribe headers'),
    fieldSpec('list_id', 'Mailing list id', 'text', 'The List-Id header'),
    fieldSpec('header', 'Header', 'text', 'Any header, by name', null, [], 'Header name'),
    fieldSpec('ai', 'AI (natural language)', 'ai', 'Describe the emails in plain words; Jev decides whether each email fits'),
    fieldSpec('gmail_category', 'Gmail category', 'enum', 'The Gmail inbox tab', ['gmail'], [
      { value: 'primary', label: 'Primary' },
      { value: 'social', label: 'Social' },
      { value: 'promotions', label: 'Promotions' },
      { value: 'updates', label: 'Updates' },
      { value: 'forums', label: 'Forums' },
    ]),
    fieldSpec('gmail_label', 'Gmail label', 'text_list', "Any of the message's Gmail labels, as they were when it was scanned", ['gmail']),
    fieldSpec('gmail_is_important', 'Marked important', 'bool', "Gmail's importance marker, as it was when scanned", ['gmail']),
    fieldSpec('gmail_is_starred', 'Starred', 'bool', 'Starred in Gmail, as it was when scanned', ['gmail']),
  ],
  operators: {
    text: [
      { key: 'equals', label: 'is', takes_value: true },
      { key: 'not_equals', label: 'is not', takes_value: true },
      { key: 'contains', label: 'contains', takes_value: true },
      { key: 'not_contains', label: 'does not contain', takes_value: true },
      { key: 'starts_with', label: 'starts with', takes_value: true },
      { key: 'ends_with', label: 'ends with', takes_value: true },
      { key: 'matches_regex', label: 'matches regex', takes_value: true },
      { key: 'not_matches_regex', label: 'does not match regex', takes_value: true },
      { key: 'is_empty', label: 'is empty', takes_value: false },
      { key: 'is_not_empty', label: 'is not empty', takes_value: false },
    ],
    text_list: [
      { key: 'equals', label: 'is', takes_value: true },
      { key: 'not_equals', label: 'is not', takes_value: true },
      { key: 'contains', label: 'contains', takes_value: true },
      { key: 'not_contains', label: 'does not contain', takes_value: true },
      { key: 'starts_with', label: 'starts with', takes_value: true },
      { key: 'ends_with', label: 'ends with', takes_value: true },
      { key: 'matches_regex', label: 'matches regex', takes_value: true },
      { key: 'not_matches_regex', label: 'does not match regex', takes_value: true },
      { key: 'is_empty', label: 'is empty', takes_value: false },
      { key: 'is_not_empty', label: 'is not empty', takes_value: false },
    ],
    bool: [
      { key: 'is_true', label: 'is true', takes_value: false },
      { key: 'is_false', label: 'is false', takes_value: false },
    ],
    number: [
      { key: 'eq', label: '=', takes_value: true },
      { key: 'ne', label: '≠', takes_value: true },
      { key: 'gt', label: '>', takes_value: true },
      { key: 'gte', label: '≥', takes_value: true },
      { key: 'lt', label: '<', takes_value: true },
      { key: 'lte', label: '≤', takes_value: true },
    ],
    enum: [
      { key: 'is', label: 'is', takes_value: true },
      { key: 'is_not', label: 'is not', takes_value: true },
      { key: 'in', label: 'is any of', takes_value: true },
    ],
    ai: [
      { key: 'matches', label: 'matches', takes_value: true },
      { key: 'not_matches', label: 'does not match', takes_value: true },
    ],
  },
  ai_enabled: true,
}

// ---------------------------------------------------------------------------------------------
// Scans, email, stats and home data

const scanBase = {
  inbox_email_address: '',
  started_at: null as string | null,
  discovered_at: null as string | null,
  finished_at: null as string | null,
  error: null as string | null,
  emails_processed: 0,
  emails_skipped: 0,
  emails_failed: 0,
  emails_matched: 0,
  labels_applied: 0,
  retries: 0,
  filters: [] as { id: string; name: string }[],
}
const scan = (
  id: string,
  inbox: typeof inboxWork,
  kind: 'scheduled' | 'adhoc',
  status: string,
  minutesAgo: number,
  values: Partial<typeof scanBase> & {
    emails_found: number
    window_start: string
    window_end: string
  },
) => ({
  ...scanBase,
  id,
  inbox_id: inbox.id,
  inbox_name: inbox.name,
  inbox_email_address: inbox.email_address,
  kind,
  status,
  created_at: ago(minutesAgo + 2),
  updated_at: ago(minutesAgo),
  ...values,
})

const scans = [
  scan('scan-personal-running', inboxPersonal, 'scheduled', 'running', 4, {
    window_start: ago(184),
    window_end: ago(4),
    started_at: ago(3),
    discovered_at: ago(2),
    emails_found: 84,
    emails_processed: 41,
    emails_matched: 16,
    labels_applied: 18,
  }),
  scan('scan-work', inboxWork, 'scheduled', 'completed', 60, {
    window_start: ago(240),
    window_end: ago(60),
    started_at: ago(59),
    discovered_at: ago(59),
    finished_at: ago(57),
    emails_found: 128,
    emails_processed: 128,
    emails_skipped: 0,
    emails_matched: 22,
    labels_applied: 24,
  }),
  scan('scan-adhoc', inboxWork, 'adhoc', 'completed', 1_440, {
    window_start: ago(43_200),
    window_end: ago(1_440),
    started_at: ago(1_439),
    discovered_at: ago(1_439),
    finished_at: ago(1_430),
    emails_found: 642,
    emails_processed: 642,
    emails_skipped: 37,
    emails_matched: 108,
    labels_applied: 118,
    filters: [{ id: 'filter-bills', name: 'All Banks Credit Card Bills' }],
  }),
  scan('scan-personal', inboxPersonal, 'scheduled', 'completed', 240, {
    window_start: ago(420),
    window_end: ago(240),
    started_at: ago(239),
    discovered_at: ago(239),
    finished_at: ago(236),
    emails_found: 64,
    emails_processed: 64,
    emails_matched: 11,
    labels_applied: 12,
  }),
  scan('scan-failed', inboxWork, 'scheduled', 'failed', 340, {
    window_start: ago(520),
    window_end: ago(340),
    started_at: ago(339),
    discovered_at: ago(339),
    finished_at: ago(330),
    emails_found: 96,
    emails_processed: 93,
    emails_failed: 3,
    emails_matched: 9,
    labels_applied: 9,
    retries: 3,
    error: '3 emails failed after 12 attempts',
  }),
]

const timeline = Array.from({ length: 30 }, (_, index) => ({
  start: dayStart(29 - index),
  emails: 220 + ((index * 37) % 140),
  labelled: 30 + ((index * 19) % 65),
}))

const email = (
  id: string,
  inbox: typeof inboxWork,
  from: string,
  subject: string,
  snippet: string,
  minutesAgo: number,
  emailLabels: { label: typeof labelCreditCard; filter: string }[],
) => ({
  id,
  inbox_id: inbox.id,
  inbox_name: inbox.name,
  sent_at: ago(minutesAgo),
  from_address: from,
  to_addresses: inbox.email_address,
  subject,
  snippet,
  labels: emailLabels.map(({ label, filter }) => ({
    label_id: label.id,
    display_name: label.display_name,
    color: label.color,
    filter_name: filter,
  })),
  scanned_at: ago(Math.max(1, minutesAgo - 2)),
  open_url: null,
})

const emails = [
  email(
    'mail-au',
    inboxPersonal,
    'cards@hoolibank.example',
    'Your Hooli Bank credit card statement ending 1234 - October 2026',
    'Your October statement is ready.',
    35,
    [{ label: labelCreditCard, filter: 'All Banks Credit Card Bills' }],
  ),
  email(
    'mail-initech',
    inboxWork,
    'cards@initechbank.example',
    'Your Initech Bank card statement ending XX76 - October 2026',
    'Your October statement is attached.',
    48,
    [{ label: labelCreditCard, filter: 'All Banks Credit Card Bills' }],
  ),
  email(
    'mail-yes',
    inboxPersonal,
    'statements@acmebank.example',
    'Your Acme Bank credit card e-statement',
    'The e-statement for your card is attached.',
    72,
    [{ label: labelCreditCard, filter: 'All Banks Credit Card Bills' }],
  ),
  email(
    'mail-globex',
    inboxPersonal,
    'statements@globexbank.example',
    'Globex Bank credit card statement',
    'Your monthly statement is attached.',
    96,
    [{ label: labelCreditCard, filter: 'All Banks Credit Card Bills' }],
  ),
  email(
    'mail-invoice',
    inboxWork,
    'billing@ledgerly.example',
    'Your October invoice is ready',
    'Your fictional invoice is attached to this preview message.',
    65,
    [{ label: labelReceipts, filter: 'Invoice & receipt catcher' }],
  ),
  email(
    'mail-bookshop',
    inboxPersonal,
    'orders@bookshop.example',
    'Order confirmed — Field Notes Vol. 2',
    'Thanks for your order. Keep this receipt.',
    180,
    [{ label: labelReceipts, filter: 'Receipts I might need' }],
  ),
  email(
    'mail-projects',
    inboxWork,
    'team@northstar.example',
    'Design review — sprint 24',
    'Notes and the agenda for tomorrow.',
    120,
    [{ label: labelProjects, filter: 'Northstar project mail' }],
  ),
  email(
    'mail-travel',
    inboxPersonal,
    'confirm@waypoint.example',
    'Travel confirmation: Riverton → Port Avalon',
    'Your itinerary and booking reference.',
    2_800,
    [{ label: labelTravel, filter: 'Travel confirmations' }],
  ),
  email(
    'mail-newsletter',
    inboxPersonal,
    'digest@fieldnotes.example',
    'Field notes #42 — small tools, quiet systems',
    'A newsletter about thoughtful software.',
    320,
    [],
  ),
]

const notifications = [
  {
    id: 'notification-bill',
    title: 'Hooli Bank ••1234 bill due 13 Nov',
    body: 'Total due ₹12,345.67, minimum ₹620.00',
    created_at: ago(35),
    read_at: null,
    processor_id: processor.id,
    processor_name: processor.name,
    open_url: null,
  },
  {
    id: 'notification-input',
    title: 'Credit card bills needs a PDF password',
    body: '1 email is waiting for the password of statements@globexbank.example.',
    created_at: ago(120),
    read_at: null,
    processor_id: processor.id,
    processor_name: processor.name,
    open_url: null,
  },
  {
    id: 'notification-failed',
    title: "Credit card bills couldn't read a statement",
    body: 'The PDF has no text (it may be a scanned image).',
    created_at: ago(320),
    read_at: ago(300),
    processor_id: processor.id,
    processor_name: processor.name,
    open_url: null,
  },
]

const overview = {
  window_start: ago(43_200),
  window_end: now,
  granularity: 'day',
  totals: { emails: 12_482, labelled_emails: 1_846, label_assignments: 1_913, senders: 1_102 },
  timeline,
  by_label: labels.map((label) => ({
    label_id: label.id,
    name: label.name,
    display_name: label.display_name,
    color: label.color,
    emails: label.email_count,
  })),
  by_filter: filters
    .filter((filter) => filter.emails_labelled > 0)
    .map((filter) => ({
      filter_id: filter.id,
      name: filter.name,
      label_display_name: filter.label.display_name,
      emails: filter.emails_labelled,
    })),
  by_inbox: inboxes.map((inbox, index) => ({
    inbox_id: inbox.id,
    name: inbox.name,
    email_address: inbox.email_address,
    emails: index ? 5_098 : 7_384,
  })),
  top_senders: [
    { sender: 'billing@ledgerly.example', emails: 142 },
    { sender: 'team@northstar.example', emails: 118 },
    { sender: 'cards@hoolibank.example', emails: 74 },
    { sender: 'updates@waypoint.example', emails: 61 },
    { sender: 'digest@fieldnotes.example', emails: 48 },
  ],
}

function result(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function installDemoApi() {
  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const url = new URL(
      typeof input === 'string' ? input : input instanceof Request ? input.url : input.toString(),
      window.location.origin,
    )
    if (!url.pathname.startsWith('/api/v1/')) return originalFetch(input, init)
    const method = init?.method?.toUpperCase() ?? (input instanceof Request ? input.method : 'GET')
    const path = url.pathname.slice('/api/v1'.length)

    if (method === 'POST' && (path === '/datasets/query' || path === '/datasets/rows')) {
      const body = JSON.parse(String(init?.body ?? '{}')) as QueryBody
      return result(path === '/datasets/query' ? { rows: seriesRows(body) } : recordRows(body))
    }
    if (method !== 'GET') return result({ detail: 'This is a read-only demo. Changes are disabled.' }, 403)

    if (path === '/filters/fields') return result(catalogue)
    if (path === '/filters') return result(filters)
    if (path.startsWith('/filters/')) {
      const id = path.split('/')[2]
      return result(filters.find((filter) => filter.id === id) ?? filters[0])
    }

    if (path === '/labels') return result(labels)
    if (path.startsWith('/labels/')) {
      const [, , id, detail] = path.split('/')
      const label = labels.find((item) => item.id === id) ?? labels[0]
      if (detail === 'stats') {
        return result({
          label_id: label.id,
          granularity: 'day',
          emails: label.email_count,
          emails_last_30_days: Math.round(label.email_count / 3),
          first_sent_at: ago(40_000),
          last_sent_at: ago(35),
          timeline,
          by_filter: filters
            .filter((filter) => filter.label.id === label.id)
            .map((filter) => ({
              filter_id: filter.id,
              name: filter.name,
              label_display_name: filter.label.display_name,
              emails: filter.emails_labelled,
            })),
          by_inbox: overview.by_inbox,
          top_senders: overview.top_senders,
        })
      }
      if (detail === 'emails') {
        const items = emails
          .filter((message) => message.labels.some((messageLabel) => messageLabel.label_id === label.id))
          .map((message) => {
            const matched = message.labels.find((messageLabel) => messageLabel.label_id === label.id)!
            return {
              id: message.id,
              inbox_id: message.inbox_id,
              inbox_name: message.inbox_name,
              sent_at: message.sent_at,
              from_address: message.from_address,
              subject: message.subject,
              snippet: message.snippet,
              filter_id: filters.find((filter) => filter.name === matched.filter_name)?.id ?? null,
              filter_name: matched.filter_name,
              applied_at: message.scanned_at,
              open_url: message.open_url,
              other_labels: message.labels.filter((messageLabel) => messageLabel.label_id !== label.id),
            }
          })
        const page = Number(url.searchParams.get('page') ?? 1)
        const pageSize = Number(url.searchParams.get('page_size') ?? 25)
        return result({
          items: items.slice((page - 1) * pageSize, page * pageSize),
          total: items.length,
          page,
          page_size: pageSize,
        })
      }
      return result(label)
    }

    if (path === '/processors/kinds') return result(kinds)
    if (path.startsWith('/processors/')) {
      const [, , id, detail] = path.split('/')
      if (id !== processor.id) return result({ detail: 'No such processor' }, 404)
      if (detail === 'runs') {
        return result({ items: processorRuns, total: processorRuns.length, page: 1, page_size: 50 })
      }
      return result(processor)
    }
    if (path === '/processors') return result([processor])

    if (path.startsWith('/dashboards/')) {
      const id = path.split('/')[2]
      return result(dashboards.find((dashboard) => dashboard.id === id) ?? dashboards[0])
    }
    if (path === '/dashboards') return result(dashboards)
    if (path === '/datasets') return result(datasets)

    if (path === '/notifications') {
      return result({
        items: notifications,
        total: notifications.length,
        unread: notifications.filter((notification) => notification.read_at === null).length,
        page: 1,
        page_size: 30,
      })
    }

    if (path === '/email/inboxes') return result(inboxes)
    if (path === '/tags') {
      return result([
        { id: 'tag-work', name: 'Work' },
        { id: 'tag-personal', name: 'Personal' },
      ])
    }

    if (path === '/scans/schedule') {
      return result({
        interval_minutes: 180,
        intervals: [30, 60, 180, 360, 1440],
        timezone: 'Asia/Kolkata',
        next_run_at: new Date(Date.now() + 48 * 60_000).toISOString(),
      })
    }
    if (path === '/scans') {
      const active = url.searchParams.get('active') === 'true'
      const inboxId = url.searchParams.get('inbox_id')
      let items = active
        ? scans.filter((scan) => scan.status === 'queued' || scan.status === 'running')
        : [...scans].sort((a, b) => b.created_at.localeCompare(a.created_at))
      if (inboxId) items = items.filter((scan) => scan.inbox_id === inboxId)
      const page = Number(url.searchParams.get('page') ?? 1)
      const pageSize = Number(url.searchParams.get('page_size') ?? 25)
      return result({
        items: items.slice((page - 1) * pageSize, page * pageSize),
        total: items.length,
        page,
        page_size: pageSize,
      })
    }

    if (path === '/stats/overview') return result(overview)

    if (path === '/home/summary') {
      return result({
        scans_completed: 96,
        scans_failed: 1,
        emails_scanned: 12_482,
        emails_labelled: 1_846,
        active_filters: filters.filter((filter) => filter.status === 'active').length,
        inactive_filters: filters.filter((filter) => filter.status === 'inactive').length,
        label_months: [labelCreditCard, labelReceipts, labelProjects, labelTravel].map((label, index) => ({
          label_id: label.id,
          display_name: label.display_name,
          color: label.color,
          this_month: [12, 142, 38, 21][index],
          last_month: [9, 114, 41, 27][index],
        })),
      })
    }
    if (path === '/home/attention') {
      return result({
        inboxes_with_errors: [],
        scans_with_problems: [],
        filters_never_matched: [],
        labels_without_active_filter: [],
        inboxes_without_filters: [],
        filters_skipped_without_ai_key: [],
        inputs_needed: [],
      })
    }
    if (path === '/home/status') {
      return result({
        scan_interval_minutes: 180,
        inboxes: inboxes.map((inbox) => ({
          inbox_id: inbox.id,
          name: inbox.name,
          email_address: inbox.email_address,
          provider: inbox.provider,
          scanned_until: inbox.scanned_until,
          last_completed_scan_at: inbox.id === inboxPersonal.id ? ago(240) : ago(57),
          active_scan: inbox.id === inboxPersonal.id ? scans[0] : null,
          quota_used: 180,
          quota_limit: 900,
          quota_window_seconds: 10,
        })),
      })
    }
    if (path === '/home/recent') {
      const limit = Number(url.searchParams.get('limit') ?? 5)
      return result({
        matches: emails
          .filter((message) => message.labels.length > 0)
          .slice(0, limit)
          .map((message) => {
            const label = message.labels[0]
            return {
              email_id: message.id,
              sent_at: message.sent_at,
              from_address: message.from_address,
              subject: message.subject,
              inbox_name: message.inbox_name,
              label_id: label.label_id,
              label_display_name: label.display_name,
              label_color: label.color,
              filter_name: label.filter_name,
              applied_at: message.scanned_at,
              open_url: null,
            }
          }),
      })
    }

    if (path === '/emails') {
      const inboxId = url.searchParams.get('inbox_id')
      const labelIds = url.searchParams.getAll('label_id')
      const labelled = url.searchParams.get('labelled')
      const search = url.searchParams.get('q')?.toLowerCase()
      let items = emails
      if (inboxId) items = items.filter((message) => message.inbox_id === inboxId)
      if (labelIds.length) {
        items = items.filter((message) =>
          labelIds.every((labelId) => message.labels.some((label) => label.label_id === labelId)),
        )
      }
      if (labelled === 'true') items = items.filter((message) => message.labels.length > 0)
      if (labelled === 'false') items = items.filter((message) => message.labels.length === 0)
      if (search) {
        items = items.filter((message) =>
          `${message.from_address} ${message.subject}`.toLowerCase().includes(search),
        )
      }
      const sort = url.searchParams.get('sort') ?? 'sent_desc'
      items = [...items].sort((a, b) => {
        if (sort === 'sender_asc') return (a.from_address ?? '').localeCompare(b.from_address ?? '')
        if (sort === 'sender_desc') return (b.from_address ?? '').localeCompare(a.from_address ?? '')
        if (sort === 'subject_asc') return (a.subject ?? '').localeCompare(b.subject ?? '')
        if (sort === 'subject_desc') return (b.subject ?? '').localeCompare(a.subject ?? '')
        return sort === 'sent_asc'
          ? a.sent_at.localeCompare(b.sent_at)
          : b.sent_at.localeCompare(a.sent_at)
      })
      const sentTimes = items.map((message) => message.sent_at).sort()
      const stats = {
        emails: items.length,
        labelled: items.filter((message) => message.labels.length > 0).length,
        unlabelled: items.filter((message) => message.labels.length === 0).length,
        senders: new Set(items.map((message) => message.from_address)).size,
        inboxes: new Set(items.map((message) => message.inbox_id)).size,
        first_sent_at: sentTimes[0] ?? null,
        last_sent_at: sentTimes[sentTimes.length - 1] ?? null,
      }
      const page = Number(url.searchParams.get('page') ?? 1)
      const pageSize = Number(url.searchParams.get('page_size') ?? 25)
      return result({
        items: items.slice((page - 1) * pageSize, page * pageSize),
        total: items.length,
        page,
        page_size: pageSize,
        stats,
      })
    }

    return result({ detail: `No demo fixture for ${path}` }, 404)
  }
}
