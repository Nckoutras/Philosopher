// User-facing copy for account deletion. APPROVED 2026-09-02, applied verbatim.
//
// Collected here rather than inlined in the page so the approved strings landed
// as a single edit to a single file. The PENDING_COPY tripwire that guarded this
// module before approval lives in lib/__tests__/accountDeletionCopy.test.ts and
// stays: it is what keeps a future placeholder from shipping.
//
// typedToken is the one entry here that is NOT copy in the usual sense. It is
// the literal a user must type, compared case-sensitively, and typedLabel must
// name it exactly — a label instructing a different word (or a different case)
// makes the confirm button impossible to enable, which is invisible in review
// and total in production. A test asserts the two agree.

export const DELETE_ACCOUNT_COPY = {
  /** The link on the account screen. */
  trigger: 'Delete account',

  /** Modal heading. */
  title: 'Delete your account?',

  /** Modal body. States that it is permanent, what goes with it, that there is
   *  no recovery, and that an active subscription is cancelled. */
  body:
    'This permanently deletes your account and everything in it — conversations, ' +
    'reflections, letters, and memories. There is no way to recover them. ' +
    'If you have an active subscription, it will be canceled immediately.',

  /** The destructive button. */
  confirmLabel: 'Delete my account',

  /** Instruction above the input. Names typedToken exactly. */
  typedLabel: 'Type DELETE to confirm',

  /** What the user types. Case-sensitive. */
  typedToken: 'DELETE',

  /** Fallback when the server sends no message. */
  genericError:
    'Something went wrong. Your account was not deleted. Please try again.',
} as const
