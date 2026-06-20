'use client'

import SubPageNav from '@/components/layout/SubPageNav'

// Placeholder for the Counterview slice (DS v5). Reached from an insight card's
// "Doubt this" action. The id rides in the query string (?insightId=…) but is
// deliberately NOT read yet — wiring it in would require a useSearchParams
// Suspense boundary, which we defer until Counterview is actually built.
export default function CounterviewPage() {
  return (
    <main className="min-h-screen [min-height:100svh] flex flex-col bg-vellum px-[24px] pb-[60px]">
      <SubPageNav fallbackHref="/app/today" />

      <div className="flex-1 flex flex-col items-center justify-center text-center gap-[14px]">
        <p className="font-lora text-[11px] uppercase tracking-[0.24em] text-bronze-dark">
          The Wise Room
        </p>
        <h1 className="font-cormorant text-[34px] font-medium text-ink leading-tight">
          Counterview
        </h1>
        <p className="font-lora text-[15px] text-sepia leading-[1.65] max-w-[300px]">
          A second reading of this insight — the case against it — is on its way.
        </p>
      </div>
    </main>
  )
}
