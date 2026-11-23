import { create } from 'zustand'
import { signalBus } from '../core/SignalBus'
import { ModelDTO, ModelListSignal } from '../../../contracts/model'

interface ModelState {
  models: ModelDTO[]
  selectedModelId: string | null
  loadModels: () => Promise<void>
  setSelectedModelId: (id: string) => void
}

export const useModelStore = create<ModelState>((set, get) => ({
  models: [],
  selectedModelId: null,

  loadModels: async () => {
    if (get().models.length > 0) return
    const dtos = await signalBus.invoke<Record<string, never>, ModelDTO[]>(ModelListSignal, {})
    const defaultModel = dtos.find(m => m.is_default) ?? dtos.find(m => m.is_available)
    set({
      models: dtos,
      selectedModelId: defaultModel?.id ?? null,
    })
  },

  setSelectedModelId: (id) => set({ selectedModelId: id }),
}))
