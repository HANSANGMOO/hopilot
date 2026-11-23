// ==========================================
// Signal Names
// ==========================================

export const AttachmentLoadSignal   = 'attachment/load'   as const
export const AttachmentUnloadSignal = 'attachment/unload' as const
export const AttachmentGetSignal    = 'attachment/get'    as const
export const AttachmentDeleteSignal = 'attachment/delete' as const

// ==========================================
// Request Params
// ==========================================

/**
 * 첨부 파일 로드 요청 파라미터
 * Python: AttachmentLoadParams
 * Signal: attachment/load (invoke)
 */
export interface AttachmentLoadParams {
  path: string
  name: string
  mime_type: string
  data?: string       // base64 — present for inline (clipboard paste)
}

/**
 * 첨부 파일 제거 요청 파라미터
 * Python: AttachmentUnloadParams
 * Signal: attachment/unload (emit)
 */
export interface AttachmentUnloadParams {
  id: string
}

/**
 * 인라인 첨부 파일 삭제 요청 파라미터 (store 제거 + 디스크 파일 삭제)
 * Python: AttachmentDeleteParams
 * Signal: attachment/delete (emit)
 */
export interface AttachmentDeleteParams {
  id: string
}

/**
 * 첨부 파일 처리 결과 DTO
 * Python: AttachmentLoadDTO
 */
export interface AttachmentLoadDTO {
  id: string
  restriction: 'encrypted' | 'drm' | 'permission' | 'mip' | null
}

/**
 * 첨부 파일 데이터 조회 요청 파라미터
 * Python: AttachmentGetParams
 * Signal: attachment/get (invoke)
 */
export interface AttachmentGetParams {
  id: string
}

/**
 * 첨부 파일 데이터 조회 결과 DTO
 * Python: AttachmentGetDTO
 */
export interface AttachmentGetDTO {
  id: string
  name: string
  data: string
  mime_type: string
  type: 'image' | 'document'
  encoding: string | null
  ref: string | null
}
