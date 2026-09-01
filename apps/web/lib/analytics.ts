// Analytics contract.
//
// The call sites are real; the transport is not — yet. PR #2 backs this exact
// signature with PostHog. Until then a tracked event is a no-op in production
// and a console line in development, so the events can be read off a local run
// and the shape of `props` can be reviewed before any SDK ships.
//
// Keep props free of personal data: internal ids and enum values only. Persona
// SLUGS are fine; display names, emails, and free text are not.

export type AnalyticsProps = Record<string, string | number | boolean>

export function track(event: string, props?: AnalyticsProps): void {
  if (process.env.NODE_ENV === 'production') return
  console.debug('[analytics]', event, props ?? {})
}
