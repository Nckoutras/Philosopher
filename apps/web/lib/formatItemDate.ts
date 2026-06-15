import { formatDistanceToNow, format, differenceInDays } from 'date-fns'

export function formatItemDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  if (differenceInDays(new Date(), d) >= 7) {
    return format(d, 'MMM d, yyyy')
  }
  return formatDistanceToNow(d, { addSuffix: true })
}
