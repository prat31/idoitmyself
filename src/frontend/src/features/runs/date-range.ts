/** Local-calendar date helpers for the run timeline. Values are "YYYY-MM-DD" (an <input type="date">). */

export function toDateInput(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function localMidnight(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** Inclusive local dates [from, to] → instants [start, end) for the API. */
export function toWindow(from: string, to: string): { window_start: string; window_end: string } {
  const end = localMidnight(to)
  end.setDate(end.getDate() + 1)
  return { window_start: localMidnight(from).toISOString(), window_end: end.toISOString() }
}

/** Last N days including today. */
export function lastDays(days: number): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(from.getDate() - (days - 1))
  return { from: toDateInput(from), to: toDateInput(to) }
}

export const DATE_PRESETS = [
  { label: 'Today', days: 1 },
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
] as const
