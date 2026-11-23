import { X } from 'lucide-react'
import { cva } from 'class-variance-authority'
import IconButton from '../atoms/IconButton'

const toastVariants = cva(
  'flex items-start gap-3 rounded-lg px-4 py-3 text-sm shadow-lg w-80',
  {
    variants: {
      variant: {
        error:   'bg-red-950 border border-red-800 text-red-200',
        warning: 'bg-yellow-950 border border-yellow-800 text-yellow-200',
        info:    'bg-elevated border border-border text-text-primary',
      },
    },
    defaultVariants: { variant: 'error' },
  }
)

interface ToastProps {
  toast: { id: string; message: string; variant: 'error' | 'warning' | 'info' }
  onClose: (id: string) => void
}

export default function Toast({ toast, onClose }: ToastProps) {
  return (
    <div className={toastVariants({ variant: toast.variant })}>
      <span className="flex-1 leading-snug">{toast.message}</span>
      <IconButton
        icon={<X size={14} />}
        label="닫기"
        variant="ghost"
        size="sm"
        onClick={() => onClose(toast.id)}
      />
    </div>
  )
}
