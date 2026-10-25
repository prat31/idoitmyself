/** Local-calendar date helpers for ad hoc scan ranges. Values are "YYYY-MM-DD" (an <input type="date">). */

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

/** The inclusive last day of an exclusive [start, end) range, for display. */
export const lastDayOf = (end: string) => new Date(new Date(end).getTime() - 1)

export type RangePreset = { label: string; days?: number; months?: number; years?: number }

export const RANGE_PRESETS: RangePreset[] = [
  { label: 'Last 1 day', days: 1 },
  { label: 'Last 3 days', days: 3 },
  { label: 'Last 1 week', days: 7 },
  { label: 'Last 1 month', months: 1 },
  { label: 'Last 1 year', years: 1 },
]

/** From the same calendar day `preset` ago, up to today (both inclusive). */
export function presetRange(preset: RangePreset): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  if (preset.days) from.setDate(from.getDate() - preset.days)
  if (preset.months) from.setMonth(from.getMonth() - preset.months)
  if (preset.years) from.setFullYear(from.getFullYear() - preset.years)
  return { from: toDateInput(from), to: toDateInput(to) }
}
