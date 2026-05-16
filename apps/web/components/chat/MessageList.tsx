import type { Message } from '@/lib/api'
import MessageBubble from './MessageBubble'

interface Props {
  messages: Message[]
}

export default function MessageList({ messages }: Props) {
  const visible = messages.filter(
    (m): m is Message & { role: 'user' | 'assistant' } =>
      m.role === 'user' || m.role === 'assistant',
  )

  return (
    <div className="flex flex-col gap-3">
      {visible.map((msg) => (
        <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
      ))}
    </div>
  )
}
