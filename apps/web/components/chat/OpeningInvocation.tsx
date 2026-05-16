interface Props {
  text: string
}

export default function OpeningInvocation({ text }: Props) {
  return (
    <div className="px-2 py-4 text-center">
      <p className="font-cormorant text-[17px] italic text-charcoal leading-[1.75]">
        {text}
      </p>
    </div>
  )
}
