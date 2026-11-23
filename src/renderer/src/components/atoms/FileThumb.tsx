import { ComponentType } from 'react'
import { File, FileCode, FileSpreadsheet, FileText } from 'lucide-react'

type IconProps = { size?: number; className?: string }

const MIME_TO_ICON: Record<string, ComponentType<IconProps>> = {
  'application/pdf':   FileText,
  'text/plain':        FileText,
  'text/markdown':     FileText,
  'text/javascript':   FileCode,
  'text/typescript':   FileCode,
  'text/x-python':     FileCode,
  'application/json':  FileCode,
  'application/msword': FileText,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileText,
  'application/vnd.ms-excel': FileSpreadsheet,
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':       FileSpreadsheet,
  'application/vnd.ms-powerpoint': FileText,
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': FileText,
}

interface FileThumbProps {
  name: string
  mimeType: string
}

export default function FileThumb({ name, mimeType }: FileThumbProps) {
  const Icon = MIME_TO_ICON[mimeType] ?? File

  return (
    <div className="flex h-16 w-16 flex-col items-center justify-center gap-1 rounded-lg bg-elevated">
      <Icon size={22} className="shrink-0 text-icon" />
      <span className="w-full truncate px-1 text-center text-[10px] text-icon">{name}</span>
    </div>
  )
}
