import { useEffect, useRef } from 'react'
import { Message } from '../../types/chat'
import MessageBubble from './MessageBubble'

interface ChatWindowProps {
  messages: Message[]
}

export default function ChatWindow({ messages }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 메시지가 추가될 때마다 화면을 맨 아래로 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto p-4 pb-32">
      <div className="mx-auto mt-4 flex max-w-3xl flex-col space-y-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {/* 스크롤을 이 위치로 끌어내리기 위한 투명한 박스 */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
