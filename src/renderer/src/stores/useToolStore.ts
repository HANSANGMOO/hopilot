import { create } from 'zustand'
import { signalBus } from '../core/SignalBus'
import { ToolGroupDTO, ToolListSignal } from '../../../contracts/tool'

const BUILTIN_SOURCES = new Set(['basic', 'context'])

interface ToolState {
  availableTools: ToolGroupDTO[]
  selectedToolIds: Set<string>
  loadTools: () => Promise<void>
  toggleTool: (id: string) => void
  toggleGroup: (source: string, allToolIds: string[]) => void
}

export const useToolStore = create<ToolState>((set, get) => ({
  availableTools: [],
  selectedToolIds: new Set(),

  loadTools: async () => {
    if (get().availableTools.length > 0) return
    const groups = await signalBus.invoke<Record<string, never>, ToolGroupDTO[]>(ToolListSignal, {})
    const defaultIds = groups
      .filter(g => BUILTIN_SOURCES.has(g.source))
      .flatMap(g => (g.tools ?? []).map(t => t.id))
    set({
      availableTools: groups,
      selectedToolIds: new Set(defaultIds),
    })
  },

  toggleTool: (id) =>
    set(state => {
      const next = new Set(state.selectedToolIds)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return { selectedToolIds: next }
    }),

  toggleGroup: (_, allToolIds) =>
    set(state => {
      const next = new Set(state.selectedToolIds)
      const allEnabled = allToolIds.every(id => next.has(id))
      if (allEnabled) allToolIds.forEach(id => next.delete(id))
      else allToolIds.forEach(id => next.add(id))
      return { selectedToolIds: next }
    }),
}))
