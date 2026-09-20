import { api } from '@/lib/api'
import { clearShareRef, getShareRef } from '@/lib/shareRef'

/**
 * The one thing both signup finish points do with a stored share reference.
 *
 * ONE FUNCTION BECAUSE THE RULE IS SUBTLE AND MUST NOT BE WRITTEN TWICE. Two
 * copies of "attribute if new, clear either way" drift, and the half that drifts
 * is always the clearing — it is the branch nobody is looking at.
 *
 * THE REFERENCE IS CONSUMED BY REACHING A SIGNUP OUTCOME, NOT BY SUCCEEDING.
 * Both arms clear it:
 *
 *   isNewAccount  — the account was created, the reference has been used, and a
 *                   second attribution for the same person is refused by the
 *                   database anyway.
 *   !isNewAccount — a RETURNING sign-in. Nothing to attribute, and leaving the
 *                   reference alive is the dangerous case: on a shared device it
 *                   would sit waiting to credit a different person's signup
 *                   days later.
 *
 * IT CANNOT FAIL A SIGN-IN. The call is awaited so the redirect does not race
 * it, but every error is swallowed: a person signing in must never see a
 * failure, or be held up by one, because a metric did not land. Losing the
 * attribution costs a funnel row; blocking the sign-in costs the session.
 *
 * CALLED BEFORE THE REDIRECT, deliberately. Attribution measures ORIGIN, not
 * onboarding completion — two different quantities, and the second is measured
 * elsewhere. Waiting until after the welcome and disclaimer screens would add a
 * fourth leak to a number the registry already describes as a floor.
 */
export async function consumeShareRef(isNewAccount: boolean): Promise<void> {
  const ref = getShareRef()
  if (!ref) return

  if (isNewAccount) {
    try {
      await api.attributeShare(ref)
    } catch {
      // Swallowed on purpose — see above. The endpoint answers 204 whether it
      // attributed or refused, so there is nothing here worth distinguishing
      // even when the call does succeed.
    }
  }

  clearShareRef()
}
