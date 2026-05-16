interface Props {
  role: 'user' | 'assistant'
  content: string
}

export default function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] px-4 py-3 rounded-sm shadow-card font-lora text-[14px] text-safety leading-relaxed whitespace-pre-wrap ${
          isUser ? 'bg-paper' : 'bg-white'
        }`}
      >
        {content}
      </div>
    </div>
  )
}
