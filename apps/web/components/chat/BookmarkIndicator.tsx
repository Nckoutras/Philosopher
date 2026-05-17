import { Bookmark } from 'lucide-react'

interface Props {
  visible: boolean
}

export default function BookmarkIndicator({ visible }: Props) {
  if (!visible) return null
  return (
    <span className="absolute top-[8px] right-[8px] pointer-events-none" aria-hidden="true">
      <Bookmark
        size={12}
        strokeWidth={0.6}
        fill="var(--bronze)"
        color="var(--bronze-dark)"
      />
    </span>
  )
}
