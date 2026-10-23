/** Overview date ranges. Presets are relative to today in the viewer's timezone; "custom" uses from/to. */
export const RANGE_PRESETS = [
  { id: '7d', label: '7 days', days: 7 },
  { id: '30d', label: '30 days', days: 30 },
  { id: '90d', label: '90 days', days: 90 },
  { id: '12m', label: '12 months', days: 365 },
  { id: 'all', label: 'All time', days: null },
] as const

export type RangeId = (typeof RANGE_PRESETS)[number]['id'] | 'custom'

export const DEFAULT_RANGE: RangeId = '30d'

function localMidnight(value: string | Date): Date {
  if (value instanceof Date) return new Date(value.getFullYear(), value.getMonth(), value.getDate())
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** [start, end) instants for the API, or nulls for all time. */
export function resolveRange(range: RangeId, from?: string | null, to?: string | null): { start: string | null; end: string | null } {
  if (range === 'custom' && from && to) {
    const end = localMidnight(to)
    end.setDate(end.getDate() + 1)
    return { start: localMidnight(from).toISOString(), end: end.toISOString() }
  }
  const preset = RANGE_PRESETS.find((p) => p.id === range)
  if (!preset || preset.days === null) return { start: null, end: null }
  const end = localMidnight(new Date())
  end.setDate(end.getDate() + 1)
  const start = new Date(end)
  start.setDate(start.getDate() - preset.days)
  return { start: start.toISOString(), end: end.toISOString() }
}
