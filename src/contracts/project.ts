/**
 * Python: contracts/project.py
 */

// ==========================================
// Signal Names
// ==========================================

export const ProjectListSignal   = 'project/list'   as const
export const ProjectLoadSignal   = 'project/load'   as const
export const ProjectCreateSignal = 'project/create' as const
export const ProjectDeleteSignal = 'project/delete' as const
export const ProjectUpdateSignal = 'project/update' as const

// ==========================================
// Request Params
// ==========================================

export interface ProjectCreateParams {
  name: string
  workspace: string
}

export interface ProjectLoadParams {
  project_id: string
}

export interface ProjectDeleteParams {
  project_id: string
}

export interface ProjectPatch {
  name?: string
  workspace?: string
}

export interface ProjectUpdateParams {
  project_id: string
  patch: ProjectPatch
}

// ==========================================
// Response DTOs
// ==========================================

/**
 * 프로젝트 목록 표시용 DTO (NavPanel용).
 * Python: ProjectMetaDTO
 */
export interface ProjectMetaDTO {
  id: string
  name: string
  workspace: string
  updated_at: string // ISO 8601
}

/**
 * 프로젝트 상세 DTO.
 * Python: ProjectDetailDTO
 */
export interface ProjectDetailDTO {
  id: string
  name: string
  workspace: string
  updated_at: string // ISO 8601
}
