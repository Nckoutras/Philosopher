interface Props {
  label: string
}

export default function DateGrouper({ label }: Props) {
  return (
    <div className="flex items-center gap-[8px] mt-[16px] mb-[8px]">
      <div className="flex-1 h-[0.5px] bg-edge" />
      <p className="font-lora text-[10px] text-sepia tracking-[0.18em] uppercase flex-shrink-0">
        {label}
      </p>
      <div className="flex-1 h-[0.5px] bg-edge" />
    </div>
  )
}
