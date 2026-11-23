import { Maximize2, ExternalLink, X } from 'lucide-react'
import { AttachmentGetDTO } from '../../../../../contracts/attachment'
import PdfPreview from '../../molecules/PdfPreview'

interface AttachmentPreviewPanelProps {
  preview: AttachmentGetDTO
  onClose: () => void
  onExpand: () => void
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
        <pre className="h-full w-full overflow-auto whitespace-pre-wrap p-4 text-sm text-text-primary">
          {preview.data}
        </pre>
      )
    default:
      return null
  }
}

export default function AttachmentPreviewPanel({ preview, onClose, onExpand }: AttachmentPreviewPanelProps) {
  return (
    <aside className="flex w-[360px] shrink-0 flex-col border-l border-border-strong bg-surface">
      <div className="flex h-12 items-center justify-between border-b border-border-strong px-4">
        <span className="truncate text-xs text-text-tertiary">{preview.name}</span>
        <div className="ml-2 flex shrink-0 items-center gap-1">
          {preview.ref && (
            <button
              onClick={() => window.api.invoke('open-path', preview.ref!)}
              className="text-text-tertiary hover:text-text-primary"
              title="시스템 기본 앱으로 열기"
            >
              <ExternalLink size={14} />
            </button>
          )}
          <button onClick={onExpand} className="text-text-tertiary hover:text-text-primary">
            <Maximize2 size={14} />
          </button>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-primary">
            <X size={16} />
          </button>
        </div>
      </div>
      <div
        className={`flex flex-1 items-center justify-center overflow-hidden p-4 ${preview.type === 'image' ? 'cursor-zoom-in' : ''}`}
        onClick={preview.type === 'image' ? onExpand : undefined}
      >
        <PreviewContent preview={preview} />
      </div>
    </aside>
  )
}
