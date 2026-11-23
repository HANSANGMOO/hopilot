import { create } from 'zustand'
import { CancellationTokenSource } from 'vscode-jsonrpc/browser'
import {
  AttachmentDeleteParams,
  AttachmentDeleteSignal,
  AttachmentGetDTO,
  AttachmentGetParams,
  AttachmentGetSignal,
  AttachmentLoadDTO,
  AttachmentLoadParams,
  AttachmentLoadSignal,
  AttachmentUnloadParams,
  AttachmentUnloadSignal,
} from '../../../contracts/attachment'
import { signalBus } from '../core/SignalBus'
import { useToastStore } from './useToastStore'
import { Attachment } from '../types/attachment'

const loadCancelSources = new Map<string, CancellationTokenSource>()

function toAttachmentType(mimeType: string): Attachment['type'] {
  if (mimeType.startsWith('image/')) return 'image'
  return 'document'
}

function withDerived(attachments: Attachment[]) {
  return {
    attachments,
    attachmentIds: attachments.map(a => a.id).filter((id): id is string => id !== null),
    isAttachmentProcessing: attachments.some(a => !a.processed),
  }
}

async function _load(path: string, name: string, mimeType: string, data?: string): Promise<AttachmentLoadDTO> {
  const source = new CancellationTokenSource()
  loadCancelSources.set(path, source)
  try {
    return await signalBus.invoke<AttachmentLoadParams, AttachmentLoadDTO>(
      AttachmentLoadSignal,
      { path, name, mime_type: mimeType, data },
      source.token,
    )
  } finally {
    loadCancelSources.delete(path)
  }
}

interface AttachmentState {
  attachments: Attachment[]
  attachmentIds: string[]
  isAttachmentProcessing: boolean
  preview: AttachmentGetDTO | null
  previewLoading: boolean
  addAttachment: (path: string, name: string, mimeType: string) => void
  addPastedAttachment: (files: File[]) => void
  removeAttachment: (path: string) => void
  clearAttachments: () => void
  cancelAttachment: (path: string) => void
  openAttachmentPreview: (id: string) => Promise<void>
  closeAttachmentPreview: () => void
}

export const useAttachmentStore = create<AttachmentState>((set, get) => ({
  attachments: [],
  attachmentIds: [],
  isAttachmentProcessing: false,
  preview: null,
  previewLoading: false,

  addAttachment: (path, name, mimeType) => {
    set(state => withDerived([...state.attachments, {
      id: null, type: toAttachmentType(mimeType), path, name, mimeType, processed: false,
    }]))
    _load(path, name, mimeType)
      .then(({ id, restriction }) => {
        set(state => withDerived(state.attachments.map(a =>
          a.path === path ? { ...a, id, restriction: restriction ?? undefined, processed: true } : a
        )))
      })
      .catch((err) => {
        set(state => withDerived(state.attachments.filter(a => a.path !== path)))
        useToastStore.getState().addToast((err as any)?.message ?? '파일을 불러오지 못했습니다.')
      })
  },

  addPastedAttachment: (files) => {
    files.forEach(file => {
      const now = new Date()
      const pad = (n: number) => n.toString().padStart(2, '0')
      const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
      const suffix = Math.random().toString(36).slice(2, 7)
      const tempPath = `paste://${now.getTime()}-${suffix}`
      const ext = file.type.split('/')[1] || 'png'
      const name = `pasted-image-${dateStr}-${suffix}.${ext}`

      set(state => withDerived([...state.attachments, {
        id: null, type: 'image', path: tempPath, name, mimeType: file.type, processed: false, inline: true,
      }]))

      const reader = new FileReader()
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1]
        _load(tempPath, name, file.type, base64)
          .then(({ id, restriction }) => {
            set(state => withDerived(state.attachments.map(a =>
              a.path === tempPath ? { ...a, id, restriction: restriction ?? undefined, processed: true } : a
            )))
          })
          .catch(() => {
            set(state => withDerived(state.attachments.filter(a => a.path !== tempPath)))
          })
      }
      reader.readAsDataURL(file)
    })
  },

  removeAttachment: (path) => {
    const target = get().attachments.find(a => a.path === path)
    if (target?.id) {
      if (target.inline) {
        signalBus.emit<AttachmentDeleteParams>(AttachmentDeleteSignal, { id: target.id })
      } else {
        signalBus.emit<AttachmentUnloadParams>(AttachmentUnloadSignal, { id: target.id })
      }
    }
    set(state => withDerived(state.attachments.filter(a => a.path !== path)))
  },

  clearAttachments: () => {
    get().attachments.forEach(a => {
      if (a.id) signalBus.emit<AttachmentUnloadParams>(AttachmentUnloadSignal, { id: a.id })
    })
    set(withDerived([]))
  },

  cancelAttachment: (path) => {
    loadCancelSources.get(path)?.cancel()
    set(state => withDerived(state.attachments.filter(a => a.path !== path)))
  },

  openAttachmentPreview: async (id) => {
    set({ previewLoading: true })
    try {
      const data = await signalBus.invoke<AttachmentGetParams, AttachmentGetDTO>(AttachmentGetSignal, { id })
      set({ preview: data })
    } finally {
      set({ previewLoading: false })
    }
  },

  closeAttachmentPreview: () => set({ preview: null }),
}))
