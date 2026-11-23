import { useEffect } from 'react'
import { X } from 'lucide-react'
import { AttachmentGetDTO } from '../../../../../contracts/attachment'
import PdfPreview from '../../molecules/PdfPreview'

interface AttachmentPreviewModalProps {
  preview: AttachmentGetDTO
  onClose: () => void
}

function PreviewContent({ preview }: { preview: AttachmentGetDTO }) {
  switch (preview.type) {
    case 'image':
      return (
        <img
          src={`data:${preview.mime_type};base64,${preview.data}`}
          alt=""
          className="max-h-full max-w-full object-contain"
        />
      )
    case 'document':
      if (preview.encoding === 'base64' && preview.mime_type === 'application/pdf') {
        return <PdfPreview data={preview.data} />
      }
      if (preview.encoding === 'base64') {
        return (
          <div className="flex items-center justify-center text-sm text-text-tertiary">
            미리보기를 지원하지 않는 파일 형식입니다.
          </div>
        )
      }
      return (
        <pre className="h-full w-full overflow-auto whitespace-pre-wrap p-6 text-sm text-text-primary">
          {preview.data}
        </pre>
      )
    default:
      return null
  }
}

export default function AttachmentPreviewModal({ preview, onClose }: AttachmentPreviewModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex cursor-pointer flex-col bg-base" onClick={onClose}>
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <span className="text-xs text-text-tertiary">{preview.name}</span>
        <button onClick={e => { e.stopPropagation(); onClose() }} className="text-text-tertiary hover:text-text-primary">
          <X size={18} />
        </button>
      </div>
      <div className="flex flex-1 items-center justify-center overflow-hidden p-6">
        <PreviewContent preview={preview} />
      </div>
    </div>
  )
}
