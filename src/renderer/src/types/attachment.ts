export type AttachmentType = 'image' | 'document'
export type AttachmentRestriction = 'encrypted' | 'drm' | 'permission' | 'mip'

export interface Attachment {
  id: string | null        // null: 백엔드 처리 대기 중
  type: AttachmentType
  path: string             // 로컬 OS 경로 (임시 식별자로도 사용)
  name: string
  mimeType: string
  processed: boolean
  restriction?: AttachmentRestriction
  inline?: boolean         // true: 클립보드 붙여넣기 — 제거 시 디스크 파일도 삭제
}

// show-open-dialog IPC 반환 타입
export interface IpcAttachmentResult {
  path: string
  name: string
  mimeType: string
}
