import { ContentBlock } from '../../../types/session'
import ExpandableBlock from '../../molecules/ExpandableBlock'

export default function UsageBlock({ block }: { block: ContentBlock }) {
  const t = block.tokens
  if (!t) return null

  return (
    <ExpandableBlock variant="bare" width="fit" showArrow={false} hoverStyle="bare" label={<span className="text-xs text-text-muted hover:text-text-primary transition-colors px-1 py-0.5">in {t.input} · out {t.output}</span>}>
      <div className="flex flex-col gap-0.5 text-xs text-text-muted items-end">
        <span>input <span className="text-text-tertiary">{t.input}</span></span>
        <span>output <span className="text-text-tertiary">{t.output}</span></span>
        {t.thinking != null && t.thinking > 0 && (
          <span>thinking <span className="text-purple-400/70">{t.thinking}</span></span>
        )}
        {t.cached != null && t.cached > 0 && (
          <span>cached <span className="text-green-400/70">{t.cached}</span></span>
        )}
        {t.cache_creation != null && t.cache_creation > 0 && (
          <span>cache created <span className="text-yellow-500/70">{t.cache_creation}</span></span>
        )}
        {t.total != null && (
          <span>total <span className="text-text-tertiary">{t.total}</span></span>
        )}
      </div>
    </ExpandableBlock>
  )
}
