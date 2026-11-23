import { createContext, useContext } from 'react'

interface SessionState {
  streamingSessions: Map<string, boolean>
}

export const SessionContext = createContext<SessionState>({ streamingSessions: new Map() })

export function useSessionContext(): SessionState {
  return useContext(SessionContext)
}
