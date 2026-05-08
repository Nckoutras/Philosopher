'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

export const dynamic = 'force-dynamic'

export default function VerifyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get('email') ?? ''

  const [code, setCode] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!email) router.replace('/auth')
  }, [email, router])

  const isValid = /^[0-9]{6}$/.test(code)
  const canSubmit = isValid && !isLoading

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return

    setIsLoading(true)

    try {
      const data = await api.verifyOtp(email, code)
      useStore.getState().setAuth(data.user, data.access_token)
      router.push('/app/dashboard')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong'
      const lower = message.toLowerCase()

      if (lower.includes('expir') || message.includes('410')) {
        toast.error('Code expired. Request a new one.')
      } else if (lower.includes('lock') || lower.includes('many') || message.includes('423')) {
        toast.error('Too many attempts. Request a new code.')
      } else if (lower.includes('invalid') || lower.includes('incorrect') || message.includes('401')) {
        toast.error('That code isn’t right.')
      } else {
        toast.error('We couldn’t verify that code. Try again.')
      }
      setIsLoading(false)
    }
  }

  const termsUrl = process.env.NEXT_PUBLIC_TERMS_URL ?? '#'
  const privacyUrl = process.env.NEXT_PUBLIC_PRIVACY_URL ?? '#'

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">
          <header className="text-center space-y-2">
            <h1 className="font-cormorant text-[28px] font-normal text-ink leading-tight">
              Enter your code.
            </h1>
            <p className="font-lora text-[13px] text-charcoal">
              We sent a 6-digit code to{' '}
              <span className="text-ink">{email}</span>.
            </p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-3">
            <label htmlFor="code" className="sr-only">
              6-digit verification code
            </label>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              autoComplete="one-time-code"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              maxLength={6}
              autoFocus
              required
              value={code}
              onChange={(e) =>
                setCode(e.target.value.replace(/\D/g, '').slice(0, 6))
              }
              placeholder="6-digit code"
              disabled={isLoading}
              className="w-full h-[50px] px-[14px] bg-white border-[0.5px] border-edge rounded-sm font-lora text-[14px] text-ink placeholder:text-sepia focus:border focus:border-ink focus:outline-none disabled:opacity-60 text-center tracking-[0.4em]"
            />
            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Verifying…' : 'Continue'}
            </button>
          </form>
        </div>
      </div>

      <footer className="px-7 py-[22px]">
        <p className="font-lora text-[11px] text-sepia text-center leading-relaxed max-w-[320px] mx-auto">
          By continuing, you agree to our{' '}
          <a href={termsUrl} target="_blank" rel="noopener noreferrer"
             className="text-ink underline underline-offset-2 decoration-[0.5px]">
            Terms
          </a>{' '}
          and{' '}
          <a href={privacyUrl} target="_blank" rel="noopener noreferrer"
             className="text-ink underline underline-offset-2 decoration-[0.5px]">
            Privacy Policy
          </a>
          .
        </p>
      </footer>
    </main>
  )
}
