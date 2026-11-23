import { createContext, useContext } from 'react'

interface MessageActions {
  deleteMessage: (messageId: string) => void
  editMessage: (messageId: string, newText: string) => Promise<void>
  retryMessage: (messageId: string, text: string) => Promise<void>
}

export const MessageActionsContext = createContext<MessageActions | null>(null)

export function useMessageActions(): MessageActions {
  const ctx = useContext(MessageActionsContext)
  if (!ctx) throw new Error('useMessageActions must be used within MessageActionsContext.Provider')
  return ctx
}
