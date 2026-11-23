import { useCallback, useEffect, useState } from 'react'
import { signalBus } from '../core/SignalBus'
import {
  SessionCreateParams,
  SessionCreateSignal,
  SessionDeleteParams,
  SessionDeleteSignal,
  SessionForkParams,
  SessionForkSignal,
  SessionListSignal,
  SessionMetaDTO,
  SessionPatch,
  SessionUpdateParams,
  SessionUpdateSignal,
} from '../../../contracts/session'
import { Session } from '../types/session'

function fromMetaDTO(dto: SessionMetaDTO): Session {
  return {
    id: dto.id,
    title: dto.title,
    updatedAt: dto.updated_at,
    projectId: dto.project_id ?? undefined,
  }
}

export function useSession() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  const loadSessions = useCallback(async () => {
    const dtos = await signalBus.invoke<Record<string, never>, SessionMetaDTO[]>(SessionListSignal, {})
    setSessions(dtos.map(fromMetaDTO))
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const createSession = useCallback(async (title = 'New Session', projectId?: string): Promise<string> => {
    const dto = await signalBus.invoke<SessionCreateParams, SessionMetaDTO>(SessionCreateSignal, { title, ...(projectId ? { project_id: projectId } : {}) })
    const session = fromMetaDTO(dto)
    setSessions(prev => [session, ...prev])
    setActiveSessionId(session.id)
    return session.id
  }, [])

  const deleteSession = useCallback(async (id: string) => {
    await signalBus.invoke<SessionDeleteParams, void>(SessionDeleteSignal, { session_id: id })
    setSessions(prev => prev.filter(s => s.id !== id))
    setActiveSessionId(cur => (cur === id ? null : cur))
  }, [])

  const updateSession = useCallback(async (id: string, patch: SessionPatch) => {
    const dto = await signalBus.invoke<SessionUpdateParams, SessionMetaDTO>(SessionUpdateSignal, { session_id: id, patch })
    setSessions(prev => prev.map(s => s.id === id ? fromMetaDTO(dto) : s))
  }, [])

  const forkSession = useCallback(async (sessionId: string, messageId: string, projectId?: string | null): Promise<string> => {
    const dto = await signalBus.invoke<SessionForkParams, SessionMetaDTO>(SessionForkSignal, { session_id: sessionId, message_id: messageId, ...(projectId !== undefined ? { project_id: projectId } : {}) })
    const session = fromMetaDTO(dto)
    setSessions(prev => [session, ...prev])
    setActiveSessionId(session.id)
    return session.id
  }, [])

  return { sessions, activeSessionId, setActiveSessionId, loadSessions, createSession, deleteSession, updateSession, forkSession }
}
