'use client'

import { Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export const dynamic = 'force-dynamic'

function TroubleForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get('email') ?? ''

  const supportEmail =
    process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? 'nckoutras@gmail.com'

  function handleContactSupport() {
    const subject = `Account access — ${email || 'unknown'}`
    const body = [
      `Email used: ${email || '(not provided)'}`,
      `Provider attempted: Email OTP`,
      `Device: ${navigator.userAgent}`,
      `Timestamp: ${new Date().toISOString()}`,
      ``,
      `Please describe your issue below:`,
      ``,
    ].join('\n')

    window.location.href =
      `mailto:${supportEmail}` +
      `?subject=${encodeURIComponent(subject)}` +
      `&body=${encodeURIComponent(body)}`
  }

  function handleBack() {
    if (email) {
      router.push(`/auth/verify?email=${encodeURIComponent(email)}`)
    } else {
      router.push('/auth')
    }
  }

  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum">
      <div className="px-7 pt-[52px]">
        <button
          onClick={handleBack}
          aria-label="Go back"
          className="flex items-center gap-1.5 text-charcoal -ml-2 px-2 py-2"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M10 12L6 8L10 4"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="font-lora text-[13px]">Back</span>
        </button>
      </div>

      <div className="flex-1 flex flex-col justify-center px-7 py-8">
        <div className="w-full max-w-[380px] mx-auto space-y-7">
          <header className="space-y-3">
            <h1 className="font-cormorant text-[26px] font-normal text-ink leading-tight">
              Trouble accessing your email?
            </h1>
            <p className="font-lora text-[13px] text-charcoal leading-[1.65]">
              No password to reset — Great Minds uses passwordless sign-in.
              If you can't access the email tied to your account, here's
              what you can do.
            </p>
          </header>

          <div className="bg-white border-[0.5px] border-edge rounded-md px-5 py-4 space-y-1">
            <p className="font-lora text-[14px] font-medium text-ink">
              Contact support
            </p>
            <p className="font-lora text-[13px] text-charcoal leading-[1.6]">
              We'll help you regain access through identity verification.
            </p>
          </div>

          <button
            type="button"
            onClick={handleContactSupport}
            className="w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum transition-colors"
          >
            Contact support
          </button>
        </div>
      </div>
    </main>
  )
}

export default function TroublePage() {
  return (
    <Suspense fallback={null}>
      <TroubleForm />
    </Suspense>
  )
}
