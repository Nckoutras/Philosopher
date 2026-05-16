interface Props {
  personaName: string
  portraitUrl: string
}

export default function ChatHeader({ personaName, portraitUrl }: Props) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-vellum border-b border-edge">
      <div className="w-11 h-11 rounded-full overflow-hidden flex-shrink-0 bg-linen">
        {portraitUrl && (
          <img
            src={portraitUrl}
            alt={personaName}
            className="w-full h-full object-cover object-top"
          />
        )}
      </div>
      <h1 className="font-cormorant text-[20px] text-ink font-medium leading-tight">
        {personaName}
      </h1>
    </header>
  )
}
