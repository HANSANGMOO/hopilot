import { memo, useRef, useState, type JSX } from 'react'
import { ChevronDown, ChevronRight, Check, X } from 'lucide-react'
import { ContentBlock, Message } from '../../../types/session'
import Container from '../../atoms/Container'
import Header from '../../atoms/Header'
import Spinner from '../../atoms/Spinner'
import Avatar from '../../atoms/Avatar'
import Hopi from '../../atoms/Hopi'
import IconButton from '../../atoms/IconButton'
import TextBlock from './TextBlock'
import ThoughtBlock from './ThoughtBlock'
import ToolBlock from './ToolBlock'
import UsageBlock from './UsageBlock'
import AttachmentBlock from './AttachmentBlock'
import ErrorBlock from './ErrorBlock'
import { UserMsgFooter, AiMsgFooter } from '../../molecules/MsgFooter'
import { useMessageActions } from '../../../contexts/MessageActionsContext'

interface MsgBubbleProps {
  message: Message
  isFooterVisible?: boolean
}

function extractText(message: Message): string {
  return message.blocks
    .filter(b => b.type === 'text')
    .map(b => b.text ?? '')
    .join('\n')
}

const BlockRenderer = memo(function BlockRenderer({ block }: { block: ContentBlock }): JSX.Element | null {
  switch (block.type) {
    case 'text':      return <TextBlock block={block} />
    case 'thought':   return <ThoughtBlock block={block} />
    case 'tool':      return <ToolBlock block={block} />
    case 'usage':     return <div className="flex justify-end"><UsageBlock block={block} /></div>
    case 'image':
    case 'document':  return <AttachmentBlock block={block} />
    case 'error':     return <ErrorBlock block={block} />
    default:          return null
  }
})

function ToolGroup({ items }: { items: ContentBlock[] }) {
  const isAnyRunning = items.some(b => b.tool?.output === undefined)
  const [isOpen, setIsOpen] = useState(true)

  return (
    <div>
      <button onClick={() => setIsOpen(prev => !prev)} className="w-full text-left">
        <Header
          label={
            <span className="inline-flex items-center gap-1.5 text-sm text-text-primary">
              {isOpen ? <ChevronDown size={14} className="text-text-tertiary" /> : <ChevronRight size={14} className="text-text-tertiary" />}
              {isAnyRunning && <Spinner size="sm" />}
              Tools ({items.length})
            </span>
          }
          className="px-2 py-1.5"
        />
      </button>
      {isOpen && (
        <Container className="max-h-64 flex flex-col gap-1 px-2 py-1">
          {items.map((b, i) => <BlockRenderer key={i} block={b} />)}
        </Container>
      )}
    </div>
  )
}

function MsgBubble({ message, isFooterVisible = true }: MsgBubbleProps) {
  const { role, blocks, timestamp } = message
  const handleCopy = () => navigator.clipboard.writeText(extractText(message))
  const { editMessage, retryMessage } = useMessageActions()
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [editSize, setEditSize] = useState<{ width: number; height: number } | undefined>(undefined)
  const bubbleRef = useRef<HTMLDivElement>(null)

  const handleEditStart = () => {
    const el = bubbleRef.current
    if (el) setEditSize({ width: el.offsetWidth, height: el.offsetHeight })
    setEditText(extractText(message))
    setIsEditing(true)
  }

  const handleEditConfirm = async () => {
    if (!editText.trim()) return
    setIsEditing(false)
    await editMessage(message.id, editText)
  }

  const handleEditCancel = () => {
    setIsEditing(false)
    setEditText('')
  }

  if (role === 'user') {
    const attachments = blocks.filter(b => b.type === 'image' || b.type === 'document')
    return (
      <div className="group flex flex-row-reverse items-start gap-3 mt-2">
        <Avatar role="user" size="md" />
        <div className="max-w-[85%]">
          {isEditing ? (
            <div className="flex flex-col gap-2">
              <textarea
                className="rounded-2xl rounded-tr-sm bg-[var(--color-brand)] px-5 py-3.5 text-[var(--color-brand-text)] resize-none outline-none"
                style={{ width: editSize?.width, minHeight: editSize?.height }}
                value={editText}
                onChange={e => setEditText(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEditConfirm() } if (e.key === 'Escape') handleEditCancel() }}
                autoFocus
              />
              <div className="flex justify-end gap-1">
                <IconButton icon={<X size={13} />}     label="취소" size="sm" variant="ghost"   onClick={handleEditCancel} />
                <IconButton icon={<Check size={13} />} label="확인" size="sm" variant="primary" onClick={handleEditConfirm} />
              </div>
            </div>
          ) : (
            <>
              <div ref={bubbleRef} className="rounded-2xl rounded-tr-sm bg-[var(--color-brand)] px-5 py-3.5 text-[var(--color-brand-text)]">
                <div className="flex flex-col gap-2">
                  {blocks.filter(b => b.type === 'text').map((b, i) => <TextBlock key={i} block={b} />)}
                </div>
                {attachments.length > 0 && (
                  <div className="flex flex-wrap gap-2 border-t border-[var(--color-brand-text)]/30 pt-2 mt-2">
                    {attachments.map((b, i) => <AttachmentBlock key={i} block={b} />)}
                  </div>
                )}
              </div>
              <UserMsgFooter messageId={message.id} onCopy={handleCopy} onEdit={handleEditStart} onRetry={() => retryMessage(message.id, extractText(message))} />
            </>
          )}
        </div>
      </div>
    )
  }

  if (role === 'system') {
    return (
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 shrink-0">
          <div className="scale-50 origin-top-left">
            <Hopi />
          </div>
        </div>
        <span className="text-[13px] text-text-muted">
          {blocks.find(b => b.type === 'text')?.text ?? ''}
        </span>
      </div>
    )
  }

  const groupedBlocks = blocks.reduce<{ type: 'tool' | 'other'; items: ContentBlock[] }[]>((acc, b) => {
    const kind = b.type === 'tool' ? 'tool' : 'other'
    const last = acc[acc.length - 1]
    if (last?.type === kind) { last.items.push(b) }
    else { acc.push({ type: kind, items: [b] }) }
    return acc
  }, [])

  return (
    <div className="group w-full py-1 pl-2 -mt-1">
      <div className="flex flex-col gap-2">
        {groupedBlocks.map((group, gi) =>
          group.type === 'tool' ? (
            <ToolGroup key={gi} items={group.items} />
          ) : (
            group.items.map((b, i) => <BlockRenderer key={`${gi}-${i}`} block={b} />)
          )
        )}
      </div>
      {isFooterVisible && <AiMsgFooter onCopy={handleCopy} timestamp={timestamp} model={message.model} />}
    </div>
  )
}

export default memo(MsgBubble)
