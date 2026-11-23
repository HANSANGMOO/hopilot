import { useEffect, useRef, useState } from 'react'
import { AlertCircle, ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import { ToolGroupDTO, ToolItemDTO } from '../../../../../contracts/tool'
import { useToolStore } from '../../../stores/useToolStore'
import IconButton from '../../atoms/IconButton'

function ToolItem({ tool, enabled, onToggle }: { tool: ToolItemDTO; enabled: boolean; onToggle: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="w-full px-3 py-1.5 hover:bg-hover transition-colors pl-7">
      <div className="flex items-center gap-3">
        <button onClick={() => onToggle(tool.id)} className="flex items-center gap-2.5 flex-1 min-w-0 text-left">
          <span
            className={`flex-shrink-0 w-3 h-3 rounded-sm border transition-colors ${enabled ? '' : 'bg-transparent border-border-input'}`}
            style={enabled ? { backgroundColor: 'var(--color-brand)', borderColor: 'var(--color-brand)' } : undefined}
          />
          <p className={`text-xs truncate ${enabled ? 'text-tool-active' : 'text-text-tertiary'}`}>{tool.name}</p>
        </button>
        <button
          onClick={() => setExpanded(p => !p)}
          className={`flex-shrink-0 text-xs leading-none px-1.5 py-0.5 rounded transition-colors ${expanded ? 'bg-border-input text-text-primary' : 'text-icon hover:text-text-secondary'}`}
        >
          ···
        </button>
      </div>
      {expanded && (
        <p className="mt-1 text-[11px] text-icon break-words pl-5">{tool.description}</p>
      )}
    </div>
  )
}

function ToolGroupSection({ group, selectedToolIds, onToggle, onToggleGroup }: {
  group: ToolGroupDTO
  selectedToolIds: Set<string>
  onToggle: (id: string) => void
  onToggleGroup: (_source: string, allToolIds: string[]) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const hasError = !!group.error
  const toolIds = group.tools.map(t => t.id)
  const allEnabled = toolIds.length > 0 && toolIds.every(id => selectedToolIds.has(id))
  const someEnabled = toolIds.some(id => selectedToolIds.has(id))

  return (
    <div>
      <div className={`flex items-center gap-1 px-2 py-1.5 transition-colors ${hasError ? 'opacity-50' : 'hover:bg-hover'}`}>
        {hasError ? (
          <AlertCircle size={14} className="flex-shrink-0 text-red-500" />
        ) : (
          <button
            onClick={() => onToggleGroup(group.source, toolIds)}
            className="flex-shrink-0 w-3.5 h-3.5 rounded-sm border transition-colors flex items-center justify-center"
            style={{
              backgroundColor: allEnabled ? 'var(--color-brand)' : someEnabled ? 'var(--color-partial-select)' : 'transparent',
              borderColor: allEnabled || someEnabled ? 'var(--color-brand)' : 'var(--color-border-input)',
            }}
          >
            {someEnabled && !allEnabled && (
              <span className="block w-1.5 h-0.5 bg-blue-400 rounded-full" />
            )}
          </button>
        )}
        <button
          onClick={() => setExpanded(p => !p)}
          className="flex items-center gap-1.5 flex-1 min-w-0 text-left"
          disabled={hasError}
        >
          <span className="text-icon">
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </span>
          <p
            className="text-[11px] font-semibold uppercase tracking-wider truncate text-text-tertiary"
            style={hasError ? { color: '#f87171' } : undefined}
          >
            {group.source}
          </p>
          {hasError ? (
            <span className="text-[10px] text-red-500 ml-auto flex-shrink-0">disabled</span>
          ) : toolIds.length === 0 ? (
            <span className="text-[10px] text-text-faint ml-auto flex-shrink-0">disabled</span>
          ) : (
            <span className="text-[10px] text-text-faint ml-auto flex-shrink-0">
              {toolIds.filter(id => selectedToolIds.has(id)).length}/{toolIds.length}
            </span>
          )}
        </button>
      </div>

      {expanded && !hasError && group.tools.map(tool => (
        <ToolItem
          key={tool.id}
          tool={tool}
          enabled={selectedToolIds.has(tool.id)}
          onToggle={onToggle}
        />
      ))}

      {expanded && hasError && (
        <p className="px-4 py-2 text-[11px] text-red-400/70 break-words">{group.error}</p>
      )}
    </div>
  )
}

export default function ToolPanel() {
  const { availableTools, selectedToolIds, toggleTool, toggleGroup, loadTools } = useToolStore()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadTools()
  }, [loadTools])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    if (isOpen) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const activeCount = selectedToolIds.size
  const isEmpty = availableTools.filter(g => !g.error).every(g => g.tools.length === 0)

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <IconButton
          icon={<Wrench size={16} />}
          label="도구 선택"
          variant={activeCount > 0 ? 'primary' : 'default'}
          size="sm"
          onClick={() => setIsOpen(prev => !prev)}
        />
        {activeCount > 0 && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center w-4 h-4 rounded-full bg-[var(--color-brand)] text-[var(--color-brand-text)] text-[10px] font-semibold leading-none pointer-events-none">
            {activeCount}
          </span>
        )}
      </div>

      {isOpen && (
        <div className="absolute bottom-full mb-1 left-0 z-50 min-w-[16rem] max-w-xs rounded-lg border border-border bg-popover shadow-lg py-1 max-h-96 overflow-y-auto">
          {isEmpty ? (
            <p className="px-3 py-2 text-xs text-icon">사용 가능한 도구가 없습니다.</p>
          ) : (
            availableTools.map(group => (
              <ToolGroupSection
                key={group.source}
                group={group}
                selectedToolIds={selectedToolIds}
                onToggle={toggleTool}
                onToggleGroup={toggleGroup}
              />
            ))
          )}
        </div>
      )}
    </div>
  )
}
