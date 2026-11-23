import { startTransition, useCallback, useEffect, useRef, useState } from 'react'
import { CancellationTokenSource } from 'vscode-jsonrpc/browser'
import { signalBus } from '../core/SignalBus'
import { useToastStore } from '../stores/useToastStore'
import { ContentBlock, Message } from '../types/session'
import { CopilotRunStreamDTO, CopilotRunParams, CopilotRunStreamSignal } from '../../../contracts/copilot'
import { SessionDetailDTO, SessionLoadParams, SessionLoadSignal, SessionTruncateParams, SessionTruncateSignal } from '../../../contracts/session'

// ─── DTO → Message 변환 ────────────────────────────────────────────────────────

function fromDetailMessages(dto: SessionDetailDTO): Message[] {
  return dto.messages.map(msg => ({
    id: msg.id,
    role: msg.role as Message['role'],
    timestamp: msg.timestamp,
    model: msg.model_name,
    blocks: msg.blocks.map(b => ({
      type: b.type as ContentBlock['type'],
      text: b.text,
      thought: b.thought,
      tool: b.tool ? { name: b.tool.name, args: b.tool.args, output: b.tool.output ?? undefined } : undefined,
      tokens: b.tokens,
      ref: b.ref,
      mime_type: b.mime_type,
      name: b.name,
    })),
  }))
}

// ─── Helper ────────────────────────────────
// ──────────────────

function payloadToBlock(payload: any): ContentBlock | null {
  switch (payload.type) {
    case 'text':
      return payload.text ? { type: 'text', text: payload.text } : null
    case 'thought':
      return payload.thought ? { type: 'thought', thought: payload.thought } : null
    case 'tool_call':
      return { type: 'tool', tool: { name: payload.tool_name, args: payload.tool_args, raw_id: payload.id ?? undefined } }
    case 'tool_output':
      return { type: 'tool', tool: { name: payload.tool_name, output: payload.output, raw_id: payload.id ?? undefined } }
    case 'image':
      return payload.ref ? { type: 'image', ref: payload.ref } : null
    case 'document':
      return payload.ref ? { type: 'document', ref: payload.ref, mime_type: payload.mime_type, name: payload.name } : null
    case 'usage':
      return {
        type: 'usage',
        tokens: {
          input: payload.input_tokens,
          output: payload.output_tokens,
          thinking: payload.thinking_tokens ?? null,
          cached: payload.cached_tokens ?? null,
          cache_creation: payload.cache_creation_tokens ?? null,
          total: payload.total_tokens ?? null,
        },
      }
    case 'stream':
      if (payload.event === 'error') {
        return { type: 'error', error: payload.error_message ?? '오류가 발생했습니다.' }
      }
      return null
    default:
      return null
  }
}

function upsertBlock(blocks: ContentBlock[], newBlock: ContentBlock): ContentBlock[] {
  const last = blocks[blocks.length - 1]
  if (newBlock.type === 'text' && last?.type === 'text') {
    return [...blocks.slice(0, -1), { ...last, text: (last.text ?? '') + (newBlock.text ?? '') }]
  }
  if (newBlock.type === 'thought' && last?.type === 'thought') {
    return [...blocks.slice(0, -1), { ...last, thought: (last.thought ?? '') + (newBlock.thought ?? '') }]
  }
  if (newBlock.type === 'tool' && newBlock.tool?.raw_id && newBlock.tool?.name) {
    const idx = blocks.findLastIndex(b => b.type === 'tool' && b.tool?.raw_id === newBlock.tool!.raw_id)
    if (idx !== -1) {
      return blocks.map((b, i) => i === idx ? { ...b, tool: { ...b.tool!, ...newBlock.tool } } : b)
    }
  }
  return [...blocks, newBlock]
}

function upsertMessage(prev: Message[], msgId: string, role: string, block: ContentBlock, timestamp?: string, model?: string): Message[] {
  const exists = prev.find(m => m.id === msgId)
  if (!exists) {
    return [...prev, { id: msgId, role: role as Message['role'], blocks: [block], timestamp, model }]
  }
  return prev.map(m =>
    m.id === msgId ? { ...m, blocks: upsertBlock(m.blocks, block) } : m
  )
}

// ─── 스트리밍 취소 소스 (세션 ID → CancellationTokenSource) ──────────────────
const streamCancelSources = new Map<string, CancellationTokenSource>()

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useMessage() {
  const [messages, setMessages] = useState<Map<string, Message[]>>(new Map())
  const [streamingSessions, setStreamingSessions] = useState<Map<string, boolean>>(new Map())
  const streamingSessionsRef = useRef(streamingSessions)
  useEffect(() => { streamingSessionsRef.current = streamingSessions }, [streamingSessions])
  const addToast = useToastStore((s) => s.addToast)

  const loadMessages = useCallback(async (sessionId: string) => {
    signalBus
      .invoke<SessionLoadParams, SessionDetailDTO>(SessionLoadSignal, { session_id: sessionId })
      .then(dto => setMessages(prev => new Map(prev).set(sessionId, fromDetailMessages(dto))))
      .catch(() => addToast('세션을 불러오지 못했습니다.'))
  }, [addToast])

  const clearMessages = useCallback((sessionId: string) => {
    setMessages(prev => { const next = new Map(prev); next.delete(sessionId); return next })
  }, [])

  const sendMessage = useCallback(async (text: string, sessionId: string, modelId?: string, modelName?: string, attachmentIds?: string[], toolIds?: string[], projectId?: string) => {
    if ((!text.trim() && !attachmentIds?.length) || streamingSessionsRef.current.get(sessionId)) return

    const source = new CancellationTokenSource()
    streamCancelSources.set(sessionId, source)
    setStreamingSessions(prev => new Map(prev).set(sessionId, true))

    try {
      await signalBus.stream<CopilotRunParams, CopilotRunStreamDTO, object>(
        CopilotRunStreamSignal,
        { session_id: sessionId, query: text, model_id: modelId, project_id: projectId, attachment_ids: attachmentIds, tool_ids: toolIds },
        (chunkDTO) => {
          const chunkSessionId = chunkDTO?.session_id
          const payload = chunkDTO?.chunk?.payload
          const role    = chunkDTO?.role
          const timestamp = chunkDTO?.timestamp
          const msgId   = chunkDTO?.msg_id
          if (!chunkSessionId || !payload || !role || !msgId) return

          const block = payloadToBlock(payload)
          if (!block) return

          const model = role === 'ai' ? modelName : undefined

          startTransition(() => {
            setMessages(prev => {
              const sessionMsgs = prev.get(chunkSessionId) ?? []
              return new Map(prev).set(chunkSessionId, upsertMessage(sessionMsgs, msgId, role, block, timestamp, model))
            })
          })
        },
        source.token,
      )
    } catch (err: unknown) {
      // 취소(-32800)는 사용자가 의도한 동작이므로 토스트 없음
      const code = (err as any)?.code
      if (code !== -32800) {
        addToast((err as any)?.message ?? '메시지 전송에 실패했습니다.')
      }
    } finally {
      streamCancelSources.delete(sessionId)
      source.dispose()
      setStreamingSessions(prev => { const next = new Map(prev); next.delete(sessionId); return next })
    }
  }, [addToast])

  const cancelMessage = useCallback((sessionId: string) => {
    streamCancelSources.get(sessionId)?.cancel()
  }, [])

  const deleteMessage = useCallback(async (sessionId: string, messageId: string) => {
    await signalBus.invoke<SessionTruncateParams, object>(SessionTruncateSignal, {
      session_id: sessionId,
      message_id: messageId,
    })
    setMessages(prev => {
      const sessionMsgs = prev.get(sessionId) ?? []
      return new Map(prev).set(sessionId, sessionMsgs.slice(0, sessionMsgs.findIndex(m => m.id === messageId)))
    })
  }, [])

  return { messages, streamingSessions, sendMessage, cancelMessage, loadMessages, clearMessages, deleteMessage }
}
