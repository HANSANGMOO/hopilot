// ==========================================
// Signal Names
// ==========================================

export const CopilotRunStreamSignal = 'copilot/run' as const

// ==========================================
// Request Params
// ==========================================

/**
 * CopilotRunStreamSignal 요청 파라미터
 * Python: CopilotRunParams
 */
export interface CopilotRunParams {
  session_id: string
  query: string
  model_id?: string
  project_id?: string
  attachment_ids?: string[]
  tool_ids?: string[]
}

/**
 * 스트리밍 청크로 수신되는 Copilot 응답 데이터
 * Python: CopilotRunStreamDTO
 */
export interface CopilotRunStreamDTO {
  chunk: any
  msg_id: string
  session_id: string
  role: string
  timestamp: string // ISO 8601
}
