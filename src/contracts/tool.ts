// ==========================================
// Signal Names
// ==========================================

export const ToolListSignal = 'tool/list' as const

// ==========================================
// Response DTOs
// ==========================================

export interface ToolItemDTO {
  id: string
  name: string
  description: string
}

export interface ToolGroupDTO {
  source: string
  tools: ToolItemDTO[]
  error?: string
}
