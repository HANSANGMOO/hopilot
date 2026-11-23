import { ContentBlock } from '../../../types/session'
import ExpandableBlock from '../../molecules/ExpandableBlock'

export default function ThoughtBlock({ block }: { block: ContentBlock }) {
  if (!block.thought) return null
  return (
    <ExpandableBlock className="mb-2" label={<span className="italic text-text-tertiary">thinking...</span>}>
      <span className="text-text-tertiary italic whitespace-pre-wrap leading-relaxed">{block.thought}</span>
    </ExpandableBlock>
  )
}
