import { Check, X } from 'lucide-react'
import { ContentBlock } from '../../../types/session'
import InlineToggle from '../../molecules/InlineToggle'
import Spinner from '../../atoms/Spinner'
import CodeToolContent from '../../molecules/CodeToolContent'
import Container from '../../atoms/Container'

const CODE_TOOLS = new Set(['python_execution'])

function DefaultToolContent({ args, output }: { args?: object; output: string }) {
  const entries = args ? Object.entries(args) : []
  return (
    <div className="flex flex-col gap-2 pt-1">
      {entries.length > 0 && (
        <div>
          <p className="mb-1 text-xs text-text-muted">Input</p>
          <Container className="max-h-40 flex flex-col gap-0.5">
            {entries.map(([key, val]) => (
              <div key={key} className="flex gap-2 text-xs">
                <span className="text-text-secondary shrink-0">{key}</span>
                <span className="text-text-secondary whitespace-pre-wrap break-all">
                  {typeof val === 'string' ? val : JSON.stringify(val)}
                </span>
              </div>
            ))}
          </Container>
        </div>
      )}
      {output && (
        <div>
          <p className="mb-1 text-xs text-text-muted">Output</p>
          <Container className="max-h-40 text-xs text-text-secondary whitespace-pre-wrap">{output}</Container>
        </div>
      )}
    </div>
  )
}

export default function ToolBlock({ block }: { block: ContentBlock }) {
  const tool = block.tool
  if (!tool?.name) return null

  const isRunning = tool.output === undefined
  const isError   = !isRunning && tool.output?.trimStart().startsWith('Error:')

  const icon = isRunning
    ? <Spinner size="sm" />
    : isError
      ? <X size={14} className="text-[var(--color-tool-error)]" />
      : <Check size={14} className="text-[var(--color-tool-success)]" />

  const labelColor = isRunning ? 'text-text-tertiary' : isError ? 'text-[var(--color-tool-error)]' : 'text-text-tertiary hover:text-text-secondary'
  const label = (
    <span className={`inline-flex items-center gap-1.5 text-sm transition-colors px-1 py-0.5 ${labelColor}`}>
      {icon}
      {tool.name}
    </span>
  )

  const hasArgs = tool.args && Object.keys(tool.args).length > 0

  if (isRunning && !hasArgs) {
    return <div className="py-0.5">{label}</div>
  }

  const content = CODE_TOOLS.has(tool.name)
    ? <CodeToolContent args={tool.args ?? {}} output={tool.output ?? ''} />
    : <DefaultToolContent args={tool.args} output={tool.output ?? ''} />

  return (
    <InlineToggle label={label}>
      {content}
    </InlineToggle>
  )
}
