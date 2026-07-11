// Placeholder Quotes screen — the 5th tab route resolves here so it opens without
// a 404. PR-3 replaces this body with the quote carousel (GET /quotes). No data
// fetch here by design; plain server component.
export default function QuotesPage() {
  return (
    <main className="min-h-screen [min-height:100svh] bg-vellum flex items-center justify-center">
      <h1 className="font-cormorant text-[30px] font-medium text-ink leading-tight">
        Quotes
      </h1>
    </main>
  )
}
