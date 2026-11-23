import { create } from 'zustand'

export type ToastVariant = 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastStore {
  toasts: Toast[]
  addToast: (message: string, variant?: ToastVariant) => void
  removeToast: (id: string) => void
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (message, variant = 'error') => {
    const id = `toast_${Date.now()}`
    set((s) => {
      const next = [...s.toasts, { id, message, variant }]
      return { toasts: next.length > 3 ? next.slice(next.length - 3) : next }
    })
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4000)
  },
  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
