import { Paperclip } from 'lucide-react'
import { ContentBlock } from '../../../types/session'

export default function AttachmentBlock({ block }: { block: ContentBlock }) {
  if (!block.ref) return null
  const label = block.name ?? block.ref.split(/[/\\]/).pop() ?? block.ref

  return (
    <div className="flex items-center gap-1.5 text-xs text-blue-200/60">
      <Paperclip size={11} className="shrink-0" />
      <span className="truncate">{label}</span>
    </div>
  )
}
