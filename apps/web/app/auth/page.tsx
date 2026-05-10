'use client'

import { useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function AuthPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)

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
            <h1 className="font-cormorant text-[28px] font-normal text-ink leading-tight">
              Begin your reflection.
            </h1>
            <p className="font-lora text-[13px] text-charcoal">
              Sign up or sign in to continue.
            </p>
          </header>

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
              className="w-full h-[50px] px-[14px] bg-white border-[0.5px] border-edge rounded-sm font-lora text-[14px] text-ink placeholder:text-sepia focus:border focus:border-ink focus:outline-none disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Sending…' : 'Continue with email'}
            </button>
          </form>
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
