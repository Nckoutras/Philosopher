import { BronzeDivider } from '@/components/ui/BronzeDivider'

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-vellum px-6">
      <h1 className="font-cormorant font-light text-5xl text-ink text-center mb-4">
        Great Minds
      </h1>
      <BronzeDivider width={80} className="my-2" />
      <p className="font-lora text-sm text-charcoal text-center max-w-md mt-4 leading-relaxed">
        Under construction. Spec-compliant rebuild in progress.
      </p>
    </main>
  )
}
