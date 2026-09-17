// Locked-persona → paywall routing, in one place.
//
// WHAT WAS WRONG. A free user tapping a Pro mind in the "Choose a mind" picker got
// a red error toast reading "Persona george_orwell requires plan upgrade" — the
// backend's PermissionError text (conversation_service.py) surfaced verbatim by
// useTopicConversation. Two defects in one: a raw slug shown to a person, and an
// ERROR where the most explicit purchase intent in the product deserves a
// conversion surface. The user just asked for a Pro mind; answering with a red
// toast is the opposite of the answer.
//
// #576/#582 already wired this route from the persona detail page, AnotherMindSheet
// and the streaming refusal path. This module is the shared spelling of that route
// so a fourth caller cannot invent a fifth variant of the query string.

import { upgradeHref } from './upgradeHref'

/** The refusal text the API returns for a persona-gate 403 (FastAPI `detail`). */
const PERSONA_GATE_MARKER = 'requires plan upgrade'

/**
 * The upgrade destination for a locked mind. Mirrors AnotherMindSheet exactly —
 * `source=persona_locked` drives the paywall's benefit line (lib/upgradeCopy.ts)
 * and `persona` lets the page resolve a DISPLAY NAME. The slug travels only as a
 * query parameter for that lookup; it is never rendered.
 */
export function lockedPersonaUpgradeHref(slug: string, returnTo?: string | null): string {
  // Delegates the query-string spelling to lib/upgradeHref, which is now the one
  // place that knows how /app/upgrade is addressed -- including the returnTo
  // that gives its Close button somewhere to go (BUG-003). The `source` and
  // `persona` semantics above are unchanged.
  return upgradeHref({ source: 'persona_locked', persona: slug, returnTo })
}

/**
 * True when a thrown error is the persona gate refusing, rather than a genuine
 * failure. Matched on the API's message because that is what the client is given:
 * `api` raises an Error carrying the FastAPI `detail` string, so the 403 status is
 * not preserved by the time a page's catch block sees it.
 *
 * This is the FALLBACK path. The picker gates on `is_accessible` before calling the
 * API at all, so this only fires on a race — a tier that changed under a loaded
 * list, or a stale persona payload. It exists so that even then the user reaches the
 * paywall rather than a toast quoting a slug at them.
 */
export function isPersonaLockedError(err: unknown): boolean {
  return err instanceof Error && err.message.includes(PERSONA_GATE_MARKER)
}
