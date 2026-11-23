import { useCallback, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { IpcAttachmentResult } from '../types/attachment'
import { useToolStore } from '../stores/useToolStore'
import { useModelStore } from '../stores/useModelStore'
import { useAttachmentStore } from '../stores/useAttachmentStore'
import { useSession } from '../hooks/useSession'
import { useProject } from '../hooks/useProject'
import { useMessage } from '../hooks/useMessage'
import { useDrop } from '../hooks/useDrop'
import { useAskUser } from '../hooks/useAskUser'
import BaseTemplate from '../components/templates/BaseTemplate'
import NavPanel from '../components/organisms/NavPanel'
import HopiBody from '../components/organisms/HopiBody'
import CopilotBody from '../components/organisms/CopilotBody'
import MsgInputFooter from '../components/organisms/MsgInputFooter'
import AttachmentPreviewPanel from '../components/organisms/AttachmentPreview/Panel'
import AttachmentPreviewModal from '../components/organisms/AttachmentPreview/Modal'
import AskUserModal from '../components/organisms/AskUserModal'
import { MessageActionsContext } from '../contexts/MessageActionsContext'
import { SessionContext } from '../contexts/SessionContext'

export default function SessionPage() {
  const {
    isOpen: isAskUserOpen,
    question,
    choices,
    placeholder,
    answer: askUserAnswer,
    index: askUserIndex,
    total: askUserTotal,
    isFirst: isAskUserFirst,
    isLast: isAskUserLast,
    setAnswer: setAskUserAnswer,
    back: backAskUser,
    advance: advanceAskUser,
    selectChoice: selectAskUserChoice,
    cancel: cancelAskUser,
  } = useAskUser()
  const { selectedToolIds } = useToolStore()
  const { models, selectedModelId } = useModelStore()
  const { attachments, attachmentIds, addAttachment, addPastedAttachment, clearAttachments, preview, previewLoading, closeAttachmentPreview } = useAttachmentStore()
  const { sessions, activeSessionId, setActiveSessionId, createSession, deleteSession, updateSession, forkSession } = useSession()
  const { projects, createProject, deleteProject, updateProject } = useProject()
  const { messages, streamingSessions, sendMessage, cancelMessage, loadMessages, clearMessages, deleteMessage } = useMessage()
  const [expanded, setExpanded] = useState(false)

  const activeSession = sessions.find(s => s.id === activeSessionId)
  const title = activeSession?.title ?? ''
  const currentProjectId = activeSession?.projectId
  const isSessionStreaming = streamingSessions.get(activeSessionId ?? '') ?? false
  const sessionMessages = messages.get(activeSessionId ?? '') ?? []

  // ─── Attachment ────────────────────────────────────────
  const handleDropAttach = useCallback((files: File[]) => {
    files.forEach(file => {
      const path = window.api.getPathForFile(file)
      addAttachment(path, file.name, file.type)
    })
  }, [addAttachment])

  const { dragActive } = useDrop(handleDropAttach)

  const handleDialogAttach = useCallback((results: IpcAttachmentResult[]) => {
    results.forEach(({ path, name, mimeType }) => addAttachment(path, name, mimeType))
  }, [addAttachment])

  // ─── Session ───────────────────────────────────────────
  const handleSelectSession = (id: string) => {
    setActiveSessionId(id)
    if (!(messages.has(id) && streamingSessions.get(id))) loadMessages(id)
  }

  const handleClearSession = () => {
    if (activeSessionId) clearMessages(activeSessionId)
    setActiveSessionId(null)
  }

  const handleCreateSession = () => {
    createSession('New Session')
  }

  const handleRenameSession = (id: string, newTitle: string) => {
    updateSession(id, { title: newTitle })
  }

  const handleDeleteSession = (id: string) => {
    if (id === activeSessionId) handleClearSession()
    deleteSession(id)
  }

  // ─── Message ───────────────────────────────────────────
  const handleDeleteMessage = useCallback((messageId: string) => {
    if (activeSessionId) deleteMessage(activeSessionId, messageId)
  }, [activeSessionId, deleteMessage])

  const handleEditMessage = useCallback(async (messageId: string, newText: string) => {
    if (!activeSessionId) return
    const selectedModel = models.find(m => m.id === selectedModelId)
    const newSessionId = await forkSession(activeSessionId, messageId, currentProjectId)
    await loadMessages(newSessionId)
    sendMessage(newText, newSessionId, selectedModelId ?? undefined, selectedModel?.display_name, undefined, selectedToolIds.size > 0 ? [...selectedToolIds] : undefined, currentProjectId)
  }, [activeSessionId, forkSession, loadMessages, sendMessage, models, selectedModelId, selectedToolIds, currentProjectId])

  const handleRetryMessage = useCallback(async (messageId: string, text: string) => {
    if (!activeSessionId) return
    const selectedModel = models.find(m => m.id === selectedModelId)
    await deleteMessage(activeSessionId, messageId)
    sendMessage(text, activeSessionId, selectedModelId ?? undefined, selectedModel?.display_name, undefined, selectedToolIds.size > 0 ? [...selectedToolIds] : undefined, currentProjectId)
  }, [activeSessionId, deleteMessage, sendMessage, models, selectedModelId, selectedToolIds, currentProjectId])

  const messageActions = useMemo(() => ({
    deleteMessage: handleDeleteMessage,
    editMessage: handleEditMessage,
    retryMessage: handleRetryMessage,
  }), [handleDeleteMessage, handleEditMessage, handleRetryMessage])

  const handleSendMessage = async (text: string) => {
    if (!text.trim() && attachments.length === 0) return
    const sid = activeSessionId ?? await createSession()
    const selectedModel = models.find(m => m.id === selectedModelId)
    sendMessage(text, sid, selectedModelId ?? undefined, selectedModel?.display_name, attachmentIds.length > 0 ? attachmentIds : undefined, selectedToolIds.size > 0 ? [...selectedToolIds] : undefined, currentProjectId)
    clearAttachments()
  }

  return (
    <SessionContext.Provider value={{ streamingSessions }}>
    <MessageActionsContext.Provider value={messageActions}>
    <div className="relative h-full">
      {dragActive && (
        <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center border-2 border-dashed border-blue-400 bg-blue-400/10">
          <span className="text-sm font-medium text-blue-300">파일을 여기에 놓으세요</span>
        </div>
      )}
      <BaseTemplate
        leftPanel={
          <NavPanel
            sessions={sessions}
            activeSessionId={activeSessionId ?? undefined}
            onSelectSession={handleSelectSession}
            onDeleteSession={handleDeleteSession}
            onRenameSession={handleRenameSession}
            onCreateSession={handleCreateSession}
            projects={projects}
            onDeleteProject={deleteProject}
            onRenameProject={(id, newName) => updateProject(id, { name: newName })}
            onCreateProject={async () => {
              const workspace = await window.api.invoke('show-folder-dialog') as string | null
              if (workspace) createProject('New Project', workspace)
            }}
            onCreateSessionInProject={(id) => createSession('New Session', id)}
            onMoveToProject={(sessionId, projectId) => updateSession(sessionId, { project_id: projectId })}
            onSetWorkspace={async (projectId) => {
              const workspace = await window.api.invoke('show-folder-dialog') as string | null
              if (workspace) updateProject(projectId, { workspace })
            }}
            onHome={handleClearSession}
            onSettings={() => {}}
          />
        }
        rightPanel={
          preview
            ? <AttachmentPreviewPanel preview={preview} onClose={() => { setExpanded(false); closeAttachmentPreview() }} onExpand={() => setExpanded(true)} />
            : previewLoading
              ? <aside className="flex w-[360px] shrink-0 items-center justify-center border-l border-border-strong bg-surface"><Loader2 size={18} className="animate-spin text-text-muted" /></aside>
              : <aside className="flex flex-col border-l border-border-strong bg-surface w-[56px]" />
        }
        header={
          <header className="flex h-12 items-center border-b border-border-strong bg-base px-4">
            <span className="text-sm font-medium text-text-primary">{title}</span>
          </header>
        }
        body={sessionMessages.length === 0 ? <HopiBody /> : <CopilotBody messages={sessionMessages} isSessionStreaming={isSessionStreaming} />}
        footer={
          <div className="bg-gradient-to-t from-base via-base to-transparent p-6">
            <div className="mx-auto max-w-3xl">
              <MsgInputFooter
                onSend={handleSendMessage}
                onStop={() => cancelMessage(activeSessionId ?? '')}
                isSessionStreaming={isSessionStreaming}
                onDialogAttach={handleDialogAttach}
                onPasteAttach={addPastedAttachment}
              />
              <p className="mt-3 text-center text-xs text-text-muted">
                Hopilot은 실수를 할 수 있습니다. 중요한 내용은 직접 확인하세요.
              </p>
            </div>
          </div>
        }
      />
      {expanded && preview && (
        <AttachmentPreviewModal preview={preview} onClose={() => setExpanded(false)} />
      )}
      {isAskUserOpen && (
        <AskUserModal
          question={question}
          choices={choices}
          placeholder={placeholder}
          answer={askUserAnswer}
          index={askUserIndex}
          total={askUserTotal}
          isFirst={isAskUserFirst}
          isLast={isAskUserLast}
          onAnswerChange={setAskUserAnswer}
          onBack={backAskUser}
          onAdvance={advanceAskUser}
          onSelectChoice={selectAskUserChoice}
          onCancel={cancelAskUser}
        />
      )}
    </div>
    </MessageActionsContext.Provider>
    </SessionContext.Provider>
  )
}
