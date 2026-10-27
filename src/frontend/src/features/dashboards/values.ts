import { formatDate, formatDateTime, formatNumber } from '@/lib/format'
import type { Bucket, DashboardRange, DatasetField, Widget } from './api'

const moneyFormat = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const compactMoneyFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 })

/** A record's value for display, by the field's type. */
export function formatValue(field: DatasetField | undefined, value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  switch (field?.type) {
    case 'money':
      return moneyFormat.format(Number(value))
    case 'number':
      return formatNumber(Number(value))
    case 'date':
      return formatDate(`${String(value)}T00:00:00`)
    case 'datetime':
      return formatDateTime(String(value))
    case 'bool':
      return value ? 'Yes' : 'No'
    default:
      return String(value)
  }
}

/** An aggregate for a headline: money without the paise, counts grouped. */
export function formatAggregate(field: DatasetField | undefined, value: number | null): string {
  if (value === null) return '—'
  return field?.type === 'money' ? compactMoneyFormat.format(value) : formatNumber(Math.round(value * 100) / 100)
}

/** Sentence-case a dimension value like "purchase" or "debit"; leave others (card names) alone. */
export function groupLabel(value: string | null): string {
  if (value === null || value === '') return '(none)'
  return /^[a-z_]+$/.test(value) ? value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, ' ') : value
}

export const rangeLabels: Record<DashboardRange, string> = {
  '3m': 'Last 3 months',
  '6m': 'Last 6 months',
  '12m': 'Last 12 months',
  all: 'All time',
}

/** The range's start (the first day of the month, N-1 months back, so it includes this month), or null. */
export function rangeStart(range: DashboardRange, now = new Date()): Date | null {
  if (range === 'all') return null
  const months = { '3m': 3, '6m': 6, '12m': 12 }[range]
  return new Date(Date.UTC(now.getFullYear(), now.getMonth() - (months - 1), 1))
}

/** The same length of time just before the range, for "vs previous period". */
export function previousPeriod(range: DashboardRange, now = new Date()): { start: Date; end: Date } | null {
  const start = rangeStart(range, now)
  if (!start) return null
  const months = { '3m': 3, '6m': 6, '12m': 12 }[range as '3m' | '6m' | '12m']
  return { start: new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() - months, 1)), end: start }
}

// Buckets come back as UTC midnights of the bucket's start ("2026-10-01T00:00:00").
function bucketDate(value: string): Date {
  const [y, m, d] = value.split('T')[0].split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d))
}

function step(date: Date, bucket: Bucket): Date {
  const next = new Date(date)
  if (bucket === 'day') next.setUTCDate(next.getUTCDate() + 1)
  else if (bucket === 'week') next.setUTCDate(next.getUTCDate() + 7)
  else if (bucket === 'month') next.setUTCMonth(next.getUTCMonth() + 1)
  else next.setUTCFullYear(next.getUTCFullYear() + 1)
  return next
}

function align(date: Date, bucket: Bucket): Date {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()))
  if (bucket === 'week') d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7)) // Monday
  if (bucket === 'month' || bucket === 'year') d.setUTCDate(1)
  if (bucket === 'year') d.setUTCMonth(0)
  return d
}

/** Every bucket from the range's start (or the first bucket with data) to now, so empty periods show
 *  as zero instead of disappearing. */
export function bucketKeys(rows: { bucket: string | null }[], bucket: Bucket, start: Date | null): string[] {
  const dates = rows.flatMap((r) => (r.bucket ? [bucketDate(r.bucket)] : []))
  const first = start ? align(start, bucket) : dates.length ? new Date(Math.min(...dates.map(Number))) : null
  if (!first) return []
  const last = align(new Date(Math.max(Date.now(), ...dates.map(Number))), bucket)
  const keys: string[] = []
  for (let d = first; d <= last && keys.length < 400; d = step(d, bucket)) keys.push(d.toISOString().slice(0, 10))
  return keys
}

const shortFormats: Record<Bucket, Intl.DateTimeFormat> = {
  day: new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', timeZone: 'UTC' }),
  week: new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', timeZone: 'UTC' }),
  month: new Intl.DateTimeFormat(undefined, { month: 'short', year: '2-digit', timeZone: 'UTC' }),
  year: new Intl.DateTimeFormat(undefined, { year: 'numeric', timeZone: 'UTC' }),
}
const longFormats: Record<Bucket, Intl.DateTimeFormat> = {
  day: new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }),
  week: new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }),
  month: new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric', timeZone: 'UTC' }),
  year: new Intl.DateTimeFormat(undefined, { year: 'numeric', timeZone: 'UTC' }),
}

export function bucketLabels(key: string, bucket: Bucket): { label: string; title: string } {
  const date = bucketDate(key)
  return {
    label: shortFormats[bucket].format(date),
    title: (bucket === 'week' ? 'Week of ' : '') + longFormats[bucket].format(date),
  }
}

/** Grid columns a widget spans on wide screens (of 6); phones stack every widget. */
export const widgetSpan: Record<Widget['width'], string> = {
  full: 'lg:col-span-6',
  half: 'lg:col-span-3',
  third: 'lg:col-span-2',
}
