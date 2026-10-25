const dateFormat = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })
const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
const numberFormat = new Intl.NumberFormat()

export const formatNumber = (n: number) => numberFormat.format(n)

export const formatDate = (iso: string | Date) => dateFormat.format(new Date(iso))

const dayMonthFormat = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' })
export const formatDayMonth = (iso: string | Date) => dayMonthFormat.format(new Date(iso))

export const formatDateTime = (iso: string | Date) => dateTimeFormat.format(new Date(iso))

const timeFormat = new Intl.DateTimeFormat(undefined, { timeStyle: 'short' })
export const formatTime = (iso: string | Date) => timeFormat.format(new Date(iso))

/** "25 Oct, 3:30 pm – 4:00 pm"; the end's date is repeated only when it differs from the start's. */
export function formatTimeRange(start: string | Date, end: string | Date): string {
  const sameDay = new Date(start).toDateString() === new Date(end).toDateString()
  return `${formatDayMonth(start)}, ${formatTime(start)} – ${sameDay ? '' : `${formatDayMonth(end)}, `}${formatTime(end)}`
}

/** "3 min ago", "yesterday", … */
export function formatRelative(iso: string): string {
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31_536_000],
    ['month', 2_592_000],
    ['day', 86_400],
    ['hour', 3_600],
    ['minute', 60],
  ]
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return relativeFormat.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

/** "45s", "3m 12s", "1h 5m". */
export function formatDuration(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}


/** Display name from an RFC 5322 From header: '"Amazon.in" <ship@amazon.in>' → 'Amazon.in'. */
export function formatSender(from: string | null): string {
  if (!from) return '(unknown sender)'
  const match = from.match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/)
  return match ? match[1] || match[2] : from // '<a@b.c>' (no name) → 'a@b.c'
}

/** Address part of a From header: '"Amazon.in" <ship@amazon.in>' → 'ship@amazon.in' (null if bare). */
export function senderAddress(from: string | null): string | null {
  const match = from?.match(/<([^>]+)>\s*$/)
  return match ? match[1] : null
}
