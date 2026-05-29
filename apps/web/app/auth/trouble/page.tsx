'use client'

import { Suspense, useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

export const dynamic = 'force-dynamic'

function TroubleForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get('email') ?? ''

  const supportEmail =
    process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? 'nckoutras@gmail.com'

  const [mailtoUrl, setMailtoUrl] = useState('')

  useEffect(() => {
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

    setMailtoUrl(
      `mailto:${supportEmail}` +
      `?subject=${encodeURIComponent(subject)}` +
      `&body=${encodeURIComponent(body)}`
    )
  }, [email, supportEmail])

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
        <div className="w-full max-w-[380px] mx-auto space-y-7 text-center">
          <header className="space-y-3">
            <h1 className="font-cormorant text-[26px] font-medium text-ink leading-tight">
              Trouble accessing your email?
            </h1>
            <p className="font-lora text-[13px] text-charcoal leading-[1.65]">
              No password to reset — The Wise Room uses passwordless sign-in.
              If you can't access the email tied to your account, here's
              what you can do.
            </p>
          </header>

          <div className="bg-linen border-[0.5px] border-edge rounded-md px-5 py-4 space-y-1">
            <p className="font-lora text-[14px] font-medium text-charcoal">
              Try a different sign-in method
            </p>
            <p className="font-lora text-[13px] text-charcoal leading-[1.6]">
              Apple sign-in coming soon.
            </p>
          </div>

          <a
            href={mailtoUrl}
            className="flex items-center justify-center w-full h-[50px] rounded-sm font-cormorant text-[17px] font-medium bg-ink text-vellum no-underline transition-colors"
          >
            Contact support
          </a>
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
