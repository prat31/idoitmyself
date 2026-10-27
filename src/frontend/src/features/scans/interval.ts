/** "every 30 minutes", "every hour", "every 3 hours", "daily". */
export function intervalLabel(minutes: number): string {
  if (minutes === 1440) return 'daily'
  if (minutes === 60) return 'every hour'
  if (minutes % 60 === 0) return `every ${minutes / 60} hours`
  return `every ${minutes} minutes`
}

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

export const intervalTitle = (minutes: number) => capitalize(intervalLabel(minutes))
