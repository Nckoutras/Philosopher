export function getTimeGreeting(now: Date = new Date()): string {
  const hour = now.getHours()
  if (hour >= 5 && hour < 12) return 'Good morning.'
  if (hour >= 12 && hour < 17) return 'Good afternoon.'
  return 'Good evening.'
}

export function getGreetingWithName(fullName?: string | null, now: Date = new Date()): string {
  const base = getTimeGreeting(now)
  const firstName = fullName?.trim().split(/\s+/)[0]
  if (!firstName) return base
  return base.slice(0, -1) + ', ' + firstName + '.'
}
