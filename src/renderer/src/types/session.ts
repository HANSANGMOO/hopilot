// ==========================================
// ContentBlock
// ==========================================

export type ContentBlockType = 'text' | 'thought' | 'tool' | 'image' | 'document' | 'usage' | 'error'

export interface Tokens {
  input: number
  output: number
  thinking?: number | null
  cached?: number | null
  cache_creation?: number | null
  total?: number | null
}

export interface ToolBlock {
  name: string
  args?: object
  output?: string   // undefined = 로딩 중
  raw_id?: string   // provider tool call id (upsertBlock 매칭용)
}

export interface ContentBlock {
  type: ContentBlockType
  text?: string      // type: 'text'
  thought?: string   // type: 'thought'
  tool?: ToolBlock   // type: 'tool'
  tokens?: Tokens    // type: 'usage'
  ref?: string       // type: 'image' | 'document'
  mime_type?: string // type: 'document'
  name?: string      // type: 'document'
  error?: string     // type: 'error'
}

// ==========================================
// Message
// ==========================================

export interface Message {
  id: string           // 백엔드 형식: "msg_xxx"
  role: 'user' | 'ai' | 'system'
  blocks: ContentBlock[]
  timestamp?: string   // ISO 8601
  model?: string       // AI 메시지 생성에 사용된 모델 display_name
}

// ==========================================
// Session
// ==========================================

export interface Session {
  id: string           // 백엔드 형식: "sess_xxx"
  title: string
  updatedAt: string    // ISO 8601
  projectId?: string
}
