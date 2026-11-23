import { useState } from 'react'
import { Copy, Check, Pencil, Trash2, ThumbsUp, ThumbsDown, Undo2, RotateCcw } from 'lucide-react'
import IconButton from '../atoms/IconButton'
import { useMessageActions } from '../../contexts/MessageActionsContext'

interface UserFooterProps {
  messageId: string
  onCopy: () => void
  onEdit: () => void
  onRetry: () => void
}

interface AiFooterProps {
  onCopy: () => void
  timestamp?: string
  model?: string
}

function formatTime(iso?: string): string {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}

function usePressed(duration = 1000) {
  const [pressed, setPressed] = useState<string | null>(null)

  const press = (key: string, callback?: () => void) => {
    callback?.()
    setPressed(key)
    setTimeout(() => setPressed(null), duration)
  }

  return { pressed, press }
}

export function UserMsgFooter({ messageId, onCopy, onEdit, onRetry }: UserFooterProps) {
  const { pressed, press } = usePressed()
  const { deleteMessage } = useMessageActions()
  const [confirming, setConfirming] = useState(false)

  const handleDeleteClick = () => {
    if (!confirming) { setConfirming(true); return }
    setConfirming(false)
    deleteMessage(messageId)
  }

  return (
    <div className="flex justify-end gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {confirming ? (
        <>
          <span className="self-center text-[11px] text-red-400 mr-1">이 메시지부터 끝까지 삭제됩니다</span>
          <IconButton icon={<Trash2 size={13} />} label="확인" size="sm" variant="danger" onClick={handleDeleteClick} />
          <IconButton icon={<Undo2  size={13} />} label="취소" size="sm" variant="ghost"  onClick={() => setConfirming(false)} />
        </>
      ) : (
        <>
          <IconButton icon={pressed === 'copy' ? <Check size={13} /> : <Copy size={13} />} label="복사" size="sm" variant={pressed === 'copy' ? 'primary' : 'ghost'} onClick={() => press('copy', onCopy)} />
          <IconButton icon={<RotateCcw size={13} />} label="재시도" size="sm" variant="ghost" onClick={onRetry} />
          <IconButton icon={<Pencil size={13} />} label="편집" size="sm" variant="ghost" onClick={onEdit} />
          <IconButton icon={<Trash2 size={13} />} label="삭제" size="sm" variant="ghost"  onClick={handleDeleteClick} />
        </>
      )}
    </div>
  )
}

export function AiMsgFooter({ onCopy, timestamp, model }: AiFooterProps) {
  const { pressed, press } = usePressed()

  return (
    <div className="flex items-center gap-0.5 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
      <IconButton icon={pressed === 'copy' ? <Check size={13} /> : <Copy size={13} />} label="복사" size="sm" variant={pressed === 'copy' ? 'primary' : 'ghost'} onClick={() => press('copy', onCopy)} />
      <IconButton icon={<ThumbsUp size={13} />}   label="좋아요" size="sm" variant={pressed === 'like'    ? 'primary' : 'ghost'} onClick={() => press('like')} />
      <IconButton icon={<ThumbsDown size={13} />} label="싫어요" size="sm" variant={pressed === 'dislike' ? 'primary' : 'ghost'} onClick={() => press('dislike')} />
      {timestamp && (
        <span className="ml-1 text-[11px] text-text-faint">{formatTime(timestamp)}</span>
      )}
      {model && (
        <span className="ml-auto text-[11px] text-text-faint">{model}</span>
      )}
    </div>
  )
}
