// Patch: expose generic request method on api client
// Add this to the ApiClient class in lib/api.ts

// This file patches the api singleton to expose request publicly.
// In production you'd add `request` as a public method on ApiClient directly.

import { api as _api } from './api'

type ApiWithRequest = typeof _api & {
  request: <T>(path: string, options?: RequestInit) => Promise<T>
}

// Expose private request as public via prototype access
;((_api as any).__proto__.request) = (_api as any).request

export const apiExt = _api as ApiWithRequest
