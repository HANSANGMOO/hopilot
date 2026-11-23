import { Image, Loader2, X } from 'lucide-react'
import { useAttachmentStore } from '../../../stores/useAttachmentStore'
import FileThumb from '../../atoms/FileThumb'
import IconButton from '../../atoms/IconButton'

function ImageIcon({ name }: { name: string }) {
  return (
    <div className="flex h-16 w-16 flex-col items-center justify-center gap-1 rounded-lg bg-elevated">
      <Image size={22} className="shrink-0 text-icon" />
      <span className="w-full truncate px-1 text-center text-[10px] text-icon">{name}</span>
    </div>
  )
}

export default function AttachmentBar() {
  const { attachments, removeAttachment, openAttachmentPreview } = useAttachmentStore()
  if (attachments.length === 0) return null

  return (
    <div className="flex gap-2 overflow-x-auto px-1 pb-2 pt-2">
      {attachments.map(att => (
        <div
          key={att.path}
          className={`relative shrink-0 ${att.processed && att.id ? 'cursor-pointer' : ''}`}
          onClick={() => att.processed && att.id && openAttachmentPreview(att.id)}
        >
          {!att.processed ? (
            <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-elevated">
              <Loader2 size={20} className="animate-spin text-icon" />
            </div>
          ) : att.type === 'image' ? (
            <ImageIcon name={att.name} />
          ) : (
            <FileThumb name={att.name} mimeType={att.mimeType} />
          )}
          <IconButton
            icon={<X size={12} />}
            label="첨부 제거"
            variant="ghost"
            size="sm"
            className="absolute -right-1.5 -top-1.5 rounded-full bg-hover hover:bg-border-input"
            onClick={e => { e.stopPropagation(); removeAttachment(att.path) }}
          />
        </div>
      ))}
    </div>
  )
}
