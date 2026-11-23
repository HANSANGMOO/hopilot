/**
 * Python: contracts/session.py
 */

// ==========================================
// Signal Names
// ==========================================

export const SessionListSignal     = 'session/list'     as const
export const SessionLoadSignal     = 'session/load'     as const
export const SessionCreateSignal   = 'session/create'   as const
export const SessionDeleteSignal   = 'session/delete'   as const
export const SessionUpdateSignal   = 'session/update'   as const
export const SessionTruncateSignal = 'session/truncate' as const
export const SessionForkSignal     = 'session/fork'     as const

// ==========================================
// Request Params
// ==========================================

export interface SessionLoadParams {
  session_id: string
}

export interface SessionCreateParams {
  title: string
  project_id?: string
}

export interface SessionDeleteParams {
  session_id: string
}

export interface SessionPatch {
  title?: string
  project_id?: string | null
}

export interface SessionUpdateParams {
  session_id: string
  patch: SessionPatch
}

export interface SessionTruncateParams {
  session_id: string
  message_id: string
}

export interface SessionForkParams {
  session_id: string
  message_id: string
  project_id?: string | null
}

// ==========================================
// Response DTOs
// ==========================================

/**
 * UsagePayload 토큰 수치를 묶는 서브 DTO.
 * Python: TokensDTO
 */
export interface TokensDTO {
  input: number
  output: number
  thinking?: number | null
  cached?: number | null
  cache_creation?: number | null
  total?: number | null
}

/**
 * tool 타입 블록의 서브 DTO.
 * Python: ToolBlockDTO
 */
export interface ToolBlockDTO {
  name: string
  args: object
  output?: string | null
}

/**
 * HOChunk.payload를 평탄화한 DTO.
 * Python: BlockDTO
 */
export interface BlockDTO {
  type: 'text' | 'thought' | 'tool' | 'image' | 'document' | 'usage'
  text?: string
  thought?: string
  tool?: ToolBlockDTO  // type: 'tool'
  tokens?: TokensDTO   // type: 'usage'
  ref?: string         // type: 'image' | 'document'
  mime_type?: string   // type: 'document'
  name?: string        // type: 'document'
}

/**
 * 메시지 한 개의 DTO.
 * Python: MessageDTO
 */
export interface MessageDTO {
  id: string
  role: 'user' | 'ai' | 'system'
  blocks: BlockDTO[]
  timestamp: string // ISO 8601
  model_name?: string
}

/**
 * 세션 목록 표시용 최소 DTO (NavPanel용).
 * Python: SessionMetaDTO
 */
export interface SessionMetaDTO {
  id: string
  title: string
  updated_at: string // ISO 8601
  project_id?: string | null
}

/**
 * 세션 전체 데이터 DTO (CopilotBody용).
 * Python: SessionDetailDTO
 */
export interface SessionDetailDTO {
  id: string
  title: string
  messages: MessageDTO[]
  updated_at: string // ISO 8601
}
