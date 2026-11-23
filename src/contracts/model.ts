// ==========================================
// Signal Names
// ==========================================

export const ModelListSignal = 'model/list' as const

// ==========================================
// Response DTOs
// ==========================================

export interface ModelDTO {
  id: string
  display_name: string
  provider: string
  is_available: boolean
  is_default: boolean
}
