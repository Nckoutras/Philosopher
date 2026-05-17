interface Props {
  label: string
}

export default function DateGrouper({ label }: Props) {
  return (
    <p className="font-lora text-[10px] text-sepia tracking-[0.18em] uppercase mt-[16px] mb-[8px]">
      {label}
    </p>
  )
}
