import { useCallback, useEffect, useState } from 'react'
import { signalBus } from '../core/SignalBus'
import {
  ProjectCreateParams,
  ProjectCreateSignal,
  ProjectDeleteParams,
  ProjectDeleteSignal,
  ProjectListSignal,
  ProjectMetaDTO,
  ProjectPatch,
  ProjectUpdateParams,
  ProjectUpdateSignal,
} from '../../../contracts/project'
import { Project } from '../types/project'

function fromMetaDTO(dto: ProjectMetaDTO): Project {
  return {
    id: dto.id,
    name: dto.name,
    workspace: dto.workspace,
    updatedAt: dto.updated_at,
  }
}

export function useProject() {
  const [projects, setProjects] = useState<Project[]>([])

  const loadProjects = useCallback(async () => {
    const dtos = await signalBus.invoke<Record<string, never>, ProjectMetaDTO[]>(ProjectListSignal, {})
    setProjects(dtos.map(fromMetaDTO))
  }, [])

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  const createProject = useCallback(async (name: string, workspace: string): Promise<string> => {
    const dto = await signalBus.invoke<ProjectCreateParams, ProjectMetaDTO>(ProjectCreateSignal, { name, workspace })
    const project = fromMetaDTO(dto)
    setProjects(prev => [project, ...prev])
    return project.id
  }, [])

  const deleteProject = useCallback(async (id: string) => {
    await signalBus.invoke<ProjectDeleteParams, void>(ProjectDeleteSignal, { project_id: id })
    setProjects(prev => prev.filter(p => p.id !== id))
  }, [])

  const updateProject = useCallback(async (id: string, patch: ProjectPatch) => {
    const dto = await signalBus.invoke<ProjectUpdateParams, ProjectMetaDTO>(ProjectUpdateSignal, { project_id: id, patch })
    setProjects(prev => prev.map(p => p.id === id ? fromMetaDTO(dto) : p))
  }, [])

  return { projects, loadProjects, createProject, deleteProject, updateProject }
}
