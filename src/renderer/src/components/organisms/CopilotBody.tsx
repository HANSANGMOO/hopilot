import { useRef, useState } from 'react'
import { Virtuoso, VirtuosoHandle } from 'react-virtuoso'
import { ArrowDown } from 'lucide-react'
import { Message } from '../../types/session'
import MsgBubble from './MsgBubble'
import IconButton from '../atoms/IconButton'

interface CopilotBodyProps {
  messages: Message[]
  isSessionStreaming: boolean
}

export default function CopilotBody({ messages, isSessionStreaming }: CopilotBodyProps) {
  const lastAiId = [...messages].reverse().find(m => m.role === 'ai')?.id
  const virtuosoRef = useRef<VirtuosoHandle>(null)
  const [atBottom, setAtBottom] = useState(true)

  const scrollToBottom = () => {
    virtuosoRef.current?.scrollToIndex({ index: messages.length - 1, behavior: 'smooth', align: 'end' })
  }

  return (
    <div className="relative h-full">
      <Virtuoso
        ref={virtuosoRef}
        style={{ height: '100%' }}
        data={messages}
        followOutput="smooth"
        atBottomStateChange={setAtBottom}
        itemContent={(index, msg) => (
          <div className="mx-auto w-full max-w-3xl px-6 py-3">
            <MsgBubble
              message={msg}
              isFooterVisible={
                !(isSessionStreaming && msg.id === lastAiId) &&
                messages[index + 1]?.role !== 'ai'
              }
            />
          </div>
        )}
      />
      {!atBottom && (
        <div className="absolute bottom-4 right-6 z-10">
          <IconButton
            icon={<ArrowDown size={16} />}
            label="맨 아래로 스크롤"
            variant="default"
            size="md"
            onClick={scrollToBottom}
            className="rounded-full bg-surface/30"
          />
        </div>
      )}
    </div>
  )
}
