import { AlertCircle } from 'lucide-react'
import { ContentBlock } from '../../../types/session'

export default function ErrorBlock({ block }: { block: ContentBlock }) {
  if (!block.error) return null
  return (
    <div className="flex items-start gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2.5 text-sm text-red-400">
      <AlertCircle size={15} className="mt-0.5 shrink-0" />
      <span>{block.error}</span>
    </div>
  )
}
