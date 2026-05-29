import BookmarkIndicator from './BookmarkIndicator'

interface Props {
  id: string
  role: 'user' | 'assistant'
  content: string
  saved: boolean
  broughtIn?: boolean
}

export default function MessageBubble({ id: _id, role, content, saved, broughtIn }: Props) {
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`relative max-w-[80%] px-4 py-3 rounded-sm shadow-card font-lora text-[16px] text-safety leading-relaxed whitespace-pre-wrap ${
          isUser ? 'bg-paper' : broughtIn ? 'bg-linen' : 'bg-white'
        }`}
      >
        {!isUser && <BookmarkIndicator visible={saved} />}
        {content}
      </div>
    </div>
  )
}
