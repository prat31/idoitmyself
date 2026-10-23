import type { ColumnDatum } from '@/components/charts/column-chart'
import type { Granularity, TimelineBucket } from './api'

// Bucket starts are calendar dates ("YYYY-MM-DD") already in the viewer's timezone: parse as local dates.
function parseDay(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d)
}

const short: Record<Granularity, Intl.DateTimeFormat> = {
  day: new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' }),
  week: new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' }),
  month: new Intl.DateTimeFormat(undefined, { month: 'short', year: '2-digit' }),
}
const long: Record<Granularity, Intl.DateTimeFormat> = {
  day: new Intl.DateTimeFormat(undefined, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }),
  week: new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short', year: 'numeric' }),
  month: new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' }),
}

export const granularityLabel: Record<Granularity, string> = { day: 'Daily', week: 'Weekly', month: 'Monthly' }

export function toColumns(
  buckets: TimelineBucket[],
  granularity: Granularity,
  valuesOf: (bucket: TimelineBucket) => Record<string, number>,
): ColumnDatum[] {
  return buckets.map((bucket) => {
    const day = parseDay(bucket.start)
    return {
      key: bucket.start,
      label: short[granularity].format(day),
      title: granularity === 'week' ? `Week of ${long.week.format(day)}` : long[granularity].format(day),
      values: valuesOf(bucket),
    }
  })
}

export function bucketTitle(bucket: TimelineBucket, granularity: Granularity): string {
  return toColumns([bucket], granularity, () => ({}))[0].title
}
