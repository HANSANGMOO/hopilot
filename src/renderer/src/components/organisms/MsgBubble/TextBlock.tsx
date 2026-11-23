import { ContentBlock } from '../../../types/session'
import MarkdownRenderer from '../../../renderers/MarkdownRenderer'

export default function TextBlock({ block }: { block: ContentBlock }) {
  if (!block.text) return null
  return <MarkdownRenderer content={block.text} />
}
