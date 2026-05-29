'use client'

import { Suspense, useState, useEffect, type FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'

export const dynamic = 'force-dynamic'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'https://philosopher-api-z9l9.onrender.com/api/v1'

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  oauth_cancelled: 'Sign-in cancelled.',
  oauth_invalid_state: 'Sign-in session expired. Please try again.',
  oauth_exchange_failed: 'Google sign-in failed. Please try again.',
  oauth_userinfo_failed: 'Google sign-in failed. Please try again.',
  oauth_network_error: 'Network error during sign-in. Please try again.',
  oauth_missing_email: 'Google sign-in failed. Please try again.',
  oauth_signup_failed: 'Could not create your account. Please try again.',
  oauth_no_token: 'Sign-in failed. Please try again.',
}

function AuthForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = searchParams.get('mode') === 'signin' ? 'signin' : 'signup'
  const errorParam = searchParams.get('error')

  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [googleEnabled, setGoogleEnabled] = useState(false)

  // Show OAuth error toast on redirect-back from a failed OAuth flow
  useEffect(() => {
    if (!errorParam) return
    const message = OAUTH_ERROR_MESSAGES[errorParam] ?? 'Sign-in failed. Please try again.'
    toast.error(message)
  }, [errorParam])

  // Fetch runtime feature flags — hides Google button on fetch failure (graceful degradation)
  useEffect(() => {
    fetch(`${API_BASE}/auth/methods`)
      .then((r) => r.json())
      .then((data) => setGoogleEnabled(!!data?.google))
      .catch(() => {})
  }, [])

  const isValid = EMAIL_REGEX.test(email.trim())
  const canSubmit = isValid && !isLoading

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return

    const trimmedEmail = email.trim().toLowerCase()
    setIsLoading(true)

    try {
      await api.requestOtp(trimmedEmail)
      router.push(`/auth/verify?email=${encodeURIComponent(trimmedEmail)}`)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      if (message.toLowerCase().includes('rate') || message.includes('429')) {
        toast.error('Too many requests. Please try again in an hour.')
      } else if (message.toLowerCase().includes('invalid') || message.includes('400')) {
        toast.error('That email doesn’t look right. Try again.')
      } else {
        toast.error('We couldn’t send the code. Try again.')
      }
      setIsLoading(false)
    }
  }

  const termsUrl = process.env.NEXT_PUBLIC_TERMS_URL ?? '/legal/terms'
  const privacyUrl = process.env.NEXT_PUBLIC_PRIVACY_URL ?? '/legal/privacy'

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">
          <header className="text-center space-y-2">
            <h1 className="font-cormorant text-[28px] font-medium text-ink leading-tight">
              {mode === 'signin' ? 'Welcome back.' : 'Create your account.'}
            </h1>
            <p className="font-lora text-[13px] text-charcoal">
              {mode === 'signin'
                ? 'Enter your email to receive a code.'
                : 'We’ll send a code to your email.'}
            </p>
          </header>

          <div className="space-y-3">
            {googleEnabled && (
              <>
                {/* Full-page navigation — intentionally leaves Next.js app to reach Google */}
                <a
                  href={`${API_BASE}/auth/oauth/google`}
                  className="flex items-center justify-center gap-3 w-full h-[52px] rounded-sm bg-white border-[0.5px] border-edge font-lora text-[15px] text-ink transition-colors hover:bg-linen"
                >
                  {/* Official Google "G" mark — inline SVG, no external CDN */}
                  <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" focusable="false">
                    <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"/>
                    <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"/>
                    <path fill="#FBBC05" d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z"/>
                    <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z"/>
                  </svg>
                  Continue with Google
                </a>

                <div className="flex items-center gap-3">
                  <div className="flex-1 h-[0.5px] bg-edge" />
                  <span className="font-lora text-[11px] text-sepia">or</span>
                  <div className="flex-1 h-[0.5px] bg-edge" />
                </div>
              </>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                type="email"
                inputMode="email"
                autoComplete="email"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                disabled={isLoading}
                className="w-full h-[50px] px-[14px] text-center bg-white border-[0.5px] border-edge rounded-sm font-lora text-[14px] text-ink placeholder:text-sepia focus:border focus:border-ink focus:outline-none disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={!canSubmit}
                className="w-full h-[52px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Sending…' : 'Continue with email'}
              </button>
            </form>
          </div>
        </div>
      </div>

      <footer className="px-7 py-[22px]">
        <p className="font-lora text-[11px] text-sepia text-center leading-relaxed max-w-[320px] mx-auto">
          By continuing, you agree to our{' '}
          <a
            href={termsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink underline underline-offset-2 decoration-[0.5px]"
          >
            Terms
          </a>{' '}
          and{' '}
          <a
            href={privacyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink underline underline-offset-2 decoration-[0.5px]"
          >
            Privacy Policy
          </a>
          .
        </p>
      </footer>
    </main>
  )
}

export default function AuthPage() {
  return (
    <Suspense fallback={null}>
      <AuthForm />
    </Suspense>
  )
}
