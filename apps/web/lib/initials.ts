export function deriveInitials(user: { full_name: string | null; email: string }): string {
  const name = user.full_name?.trim()
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return parts[0][0].toUpperCase()
  }
  return ((user.email.split('@')[0][0]) ?? 'U').toUpperCase()
}
