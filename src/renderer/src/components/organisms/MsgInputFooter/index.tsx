import { useEffect, useState } from 'react'
import { Maximize2, Minimize2 } from 'lucide-react'
import { IpcAttachmentResult } from '../../../types/attachment'
import TextArea from '../../atoms/TextArea'
import AttachmentBar from './AttachmentBar'
import Toolbar from './Toolbar'

interface MsgInputFooterProps {
  onSend: (text: string) => void
  onStop: () => void
  isSessionStreaming: boolean
  onDialogAttach: (results: IpcAttachmentResult[]) => void
  onPasteAttach: (files: File[]) => void
}

const LINE_HEIGHT = 24
const EXPAND_THRESHOLD = LINE_HEIGHT * 5

function InputBox({
  input, setInput, onSend, onStop,
  isSessionStreaming,
  onDialogAttach, onPasteAttach,
  expanded, onExpandToggle,
}: MsgInputFooterProps & { input: string; setInput: (v: string) => void; expanded: boolean; onExpandToggle: () => void }) {
  const [showExpand, setShowExpand] = useState(false)

  const handleSend = () => {
    onSend(input)
    setInput('')
  }

  const handleAttachClick = async () => {
    const results = await window.api.invoke('show-open-dialog') as IpcAttachmentResult[]
    if (!results.length) return
    onDialogAttach(results)
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const files = Array.from(e.clipboardData.items)
      .filter(item => item.kind === 'file' && item.type.startsWith('image/'))
      .map(item => item.getAsFile())
      .filter((f): f is File => f !== null)
    if (!files.length) return
    e.preventDefault()
    onPasteAttach(files)
  }

  return (
    <div
      className={`msg-input-box relative flex flex-col rounded-2xl border border-border bg-surface p-2 shadow-xl transition-all ${expanded ? 'h-full overflow-hidden' : ''}`}
      onPaste={handlePaste}
    >
      {(showExpand || expanded) && (
        <button
          onClick={onExpandToggle}
          className="absolute top-2 right-2 z-10 flex items-center justify-center w-5 h-5 rounded text-text-muted hover:text-text-secondary hover:bg-hover transition-colors"
        >
          {expanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
        </button>
      )}

      <AttachmentBar />

      <div className={expanded ? 'flex-1 overflow-y-auto' : ''}>
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onSubmit={handleSend}
          placeholder="Hopilot에게 무엇이든 물어보세요..."
          className="px-3 py-2"
          expanded={expanded}
          onHeightChange={(height) => setShowExpand(height >= EXPAND_THRESHOLD)}
        />
      </div>

      <div className="mt-1 flex items-center justify-end px-1 shrink-0">
        <Toolbar
          input={input}
          isSessionStreaming={isSessionStreaming}
          onSend={handleSend}
          onStop={onStop}
          onAttachClick={handleAttachClick}
        />
      </div>
    </div>
  )
}

export default function MsgInputFooter(props: MsgInputFooterProps) {
  const [input, setInput] = useState('')
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      if (props.isSessionStreaming) { props.onStop(); return }
      if (expanded) setExpanded(false)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [expanded, props.isSessionStreaming, props.onStop])

  const handleSend = (text: string) => {
    props.onSend(text)
    setExpanded(false)
  }

  const inputBox = (
    <InputBox
      {...props}
      input={input}
      setInput={setInput}
      onSend={handleSend}
      expanded={expanded}
      onExpandToggle={() => setExpanded(p => !p)}
    />
  )

  if (expanded) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
        <div className="flex w-4/5 h-4/5 flex-col min-h-0">
          {inputBox}
        </div>
      </div>
    )
  }

  return inputBox
}
