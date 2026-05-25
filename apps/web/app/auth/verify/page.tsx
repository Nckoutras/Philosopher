'use client'

import { Suspense, useEffect, useState, useRef, type FormEvent } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { useStore } from '@/lib/store'

export const dynamic = 'force-dynamic'

function VerifyForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get('email') ?? ''

  const [code, setCode] = useState(['', '', '', '', '', ''])
  const [isLoading, setIsLoading] = useState(false)
  const refs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (!email) router.replace('/auth')
  }, [email, router])

  const fullCode = code.join('')
  const isValid = /^[0-9]{6}$/.test(fullCode)
  const canSubmit = isValid && !isLoading

  const handleChange = (i: number, value: string) => {
    const numeric = value.replace(/[^0-9]/g, '')

    // Multi-character input (autofill or paste): distribute digits
    // across boxes starting from current index. Handles full 6-digit
    // autofill AND partial autofills (2-5 digits).
    if (numeric.length > 1) {
      const next = [...code]
      for (let j = 0; j < numeric.length && (i + j) < 6; j++) {
        next[i + j] = numeric[j]
      }
      setCode(next)
      const lastFilledIdx = Math.min(i + numeric.length - 1, 5)
      refs.current[lastFilledIdx]?.focus()
      return
    }

    // Single character input (manual typing)
    const digit = numeric.slice(-1)
    const next = [...code]
    next[i] = digit
    setCode(next)
    if (digit && i < 5) refs.current[i + 1]?.focus()
  }

  const handleKeyDown = (i: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !code[i] && i > 0) {
      refs.current[i - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 6)
    const next = ['', '', '', '', '', '']
    for (let i = 0; i < pasted.length; i++) next[i] = pasted[i]
    setCode(next)
    refs.current[Math.min(pasted.length, 5)]?.focus()
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return

    setIsLoading(true)

    try {
      const data = await api.verifyOtp(email, fullCode)
      useStore.getState().setAuth(data.user, data.access_token)
      if (data.user.needs_disclaimer) {
        router.replace('/auth/disclaimer')
      } else {
        router.replace('/app/today')
      }
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

  const termsUrl = process.env.NEXT_PUBLIC_TERMS_URL ?? '/legal/terms'
  const privacyUrl = process.env.NEXT_PUBLIC_PRIVACY_URL ?? '/legal/privacy'

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
            <div className="flex gap-2 justify-center" onPaste={handlePaste}>
              {code.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => { refs.current[i] = el }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  autoComplete={i === 0 ? 'one-time-code' : 'off'}
                  maxLength={i === 0 ? 6 : 1}
                  autoFocus={i === 0}
                  value={digit}
                  onChange={(e) => handleChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  disabled={isLoading}
                  className="w-12 h-14 text-center font-cormorant text-[28px] font-normal text-ink bg-white border-[0.5px] border-edge rounded-sm focus:border focus:border-ink focus:outline-none disabled:opacity-60 caret-transparent"
                />
              ))}
            </div>
            <button
              type="submit"
              disabled={!canSubmit}
              className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum disabled:bg-linen disabled:text-charcoal disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Verifying…' : 'Continue'}
            </button>
          </form>

          <p className="text-center">
            <a
              href={`/auth/trouble${email ? `?email=${encodeURIComponent(email)}` : ''}`}
              className="font-lora text-[12px] text-charcoal underline underline-offset-2 decoration-[0.5px]"
            >
              Trouble accessing email?
            </a>
          </p>
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

export default function VerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyForm />
    </Suspense>
  )
}
