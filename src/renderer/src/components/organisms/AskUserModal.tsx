import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, MessageSquare } from 'lucide-react'
import Button from '../atoms/Button'
import TextArea from '../atoms/TextArea'
import MarkdownRenderer from '../../renderers/MarkdownRenderer'

interface AskUserModalProps {
  question: string
  choices?: string[] | null
  placeholder?: string
  answer: string
  index: number
  total: number
  isFirst: boolean
  isLast: boolean
  onAnswerChange: (value: string) => void
  onBack: () => void
  onAdvance: () => void
  onSelectChoice: (value: string) => void
  onCancel: () => void
}

function useDrag(initial: { x: number; y: number }, elRef: React.RefObject<HTMLDivElement | null>) {
  const [pos, setPos] = useState(initial)
  const dragging = useRef(false)
  const offset = useRef({ x: 0, y: 0 })

  const onHandleMouseDown = (e: React.MouseEvent) => {
    dragging.current = true
    offset.current = { x: e.clientX - pos.x, y: e.clientY - pos.y }
    e.preventDefault()
  }

  // position bottom-right using actual element size after mount
  useEffect(() => {
    const el = elRef.current
    if (!el) return
    const w = el.offsetWidth
    const h = el.offsetHeight
    setPos({
      x: window.innerWidth - w - 24,
      y: window.innerHeight - h - 24,
    })
  }, [elRef])

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!dragging.current) return
      const w = elRef.current?.offsetWidth ?? 0
      const h = elRef.current?.offsetHeight ?? 0
      setPos({
        x: Math.min(Math.max(0, e.clientX - offset.current.x), window.innerWidth - w),
        y: Math.min(Math.max(0, e.clientY - offset.current.y), window.innerHeight - h),
      })
    }
    const onMouseUp = () => { dragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [elRef])

  return { pos, onHandleMouseDown }
}

export default function AskUserModal({
  question,
  choices,
  placeholder,
  answer,
  index,
  total,
  isFirst,
  isLast,
  onAnswerChange,
  onBack,
  onAdvance,
  onSelectChoice,
  onCancel,
}: AskUserModalProps) {
  const hasChoices = choices && choices.length > 0
  const elRef = useRef<HTMLDivElement>(null)
  const { pos, onHandleMouseDown } = useDrag({ x: 0, y: 0 }, elRef)

  const handleAdvance = () => {
    if (!answer.trim()) return
    onAdvance()
  }

  return (
    <div
      ref={elRef}
      className="fixed z-50 w-96 rounded-xl border border-blue-500/40 bg-surface shadow-2xl"
      style={{ top: pos.y, left: pos.x }}
    >
      <div
        className="flex items-center gap-2 border-b border-border px-4 py-3 cursor-grab active:cursor-grabbing select-none"
        onMouseDown={onHandleMouseDown}
      >
        <MessageSquare size={15} className="text-blue-400" />
        <span className="text-sm font-medium text-text-primary">입력 요청</span>
        {total > 1 && (
          <span className="ml-auto rounded-full bg-blue-500/15 px-2 py-0.5 text-xs font-medium text-blue-400">
            {index + 1}/{total}
          </span>
        )}
      </div>

      <div className="px-4 py-4 flex flex-col gap-3">
        <div className="text-sm text-text-secondary">
          <MarkdownRenderer content={question} />
        </div>

        {hasChoices && (
          <div className="flex flex-col gap-1.5">
            {choices!.map((choice) => (
              <button
                key={choice}
                onClick={() => onSelectChoice(choice)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors hover:border-blue-500 hover:bg-blue-500/10 ${
                  answer === choice ? 'border-blue-500 bg-blue-500/10 text-text-primary' : 'border-border-input bg-base text-text-primary'
                }`}
              >
                {choice}
              </button>
            ))}
          </div>
        )}

        <div className="rounded-lg border border-border-input bg-base px-3 py-2 focus-within:border-blue-500">
          <TextArea
            autoFocus={!hasChoices}
            value={answer}
            onChange={e => onAnswerChange(e.target.value)}
            onSubmit={handleAdvance}
            placeholder={placeholder ?? (hasChoices ? '또는 직접 입력...' : '답변을 입력하세요...')}
            className="text-sm"
          />
        </div>
      </div>

      <div className="flex justify-between gap-2 border-t border-border px-4 py-3">
        <div>
          {!isFirst && (
            <Button variant="ghost" size="sm" onClick={onBack}>
              <ChevronLeft size={14} />
              이전
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel}>취소</Button>
          <Button variant="primary" size="sm" onClick={handleAdvance} disabled={!answer.trim()}>
            {isLast ? '제출' : '다음'}
          </Button>
        </div>
      </div>
    </div>
  )
}
