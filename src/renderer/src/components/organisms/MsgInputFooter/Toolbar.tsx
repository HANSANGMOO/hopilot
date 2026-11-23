import { useEffect } from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Paperclip, Send, Square, ChevronDown } from 'lucide-react'
import { useModelStore } from '../../../stores/useModelStore'
import { useAttachmentStore } from '../../../stores/useAttachmentStore'
import IconButton from '../../atoms/IconButton'
import Button from '../../atoms/Button'
import ToolPanel from './ToolPanel'
import { dropdownContent, dropdownItem } from '../../../styles/dropdown'

interface ToolbarProps {
  input: string
  isSessionStreaming: boolean
  onSend: () => void
  onStop: () => void
  onAttachClick: () => void
}

export default function Toolbar({ input, isSessionStreaming, onSend, onStop, onAttachClick }: ToolbarProps) {
  const { models, selectedModelId, setSelectedModelId, loadModels } = useModelStore()
  const { attachments, isAttachmentProcessing } = useAttachmentStore()
  const hasAttachments = attachments.length > 0
  const disabled = (!input.trim() && !hasAttachments) || isSessionStreaming || isAttachmentProcessing

  useEffect(() => {
    loadModels()
  }, [loadModels])

  const selectedLabel = models.find(m => m.id === selectedModelId)?.display_name ?? '모델 선택'

  return (
    <div className="flex items-center justify-between w-full px-1">
      <div className="flex items-center gap-1">
        <IconButton
          icon={<Paperclip size={16} />}
          label="파일 첨부"
          variant="default"
          size="sm"
          onClick={onAttachClick}
        />
        <ToolPanel />
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <Button variant="ghost" size="sm" rightIcon={<ChevronDown size={14} />}>
              {selectedLabel}
            </Button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className={dropdownContent} side="top" align="start" sideOffset={4}>
              {models.map(m => (
                <DropdownMenu.Item
                  key={m.id}
                  className={dropdownItem}
                  disabled={!m.is_available}
                  onSelect={() => setSelectedModelId(m.id)}
                >
                  {m.id === selectedModelId && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />}
                  {m.display_name}
                </DropdownMenu.Item>
              ))}
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
      {isSessionStreaming ? (
        <IconButton icon={<Square size={16} />} label="정지" variant="danger" size="lg" onClick={onStop} />
      ) : (
        <IconButton
          icon={<Send size={18} className="ml-0.5" />}
          label="전송"
          variant={disabled ? 'default' : 'primary'}
          size="lg"
          onClick={onSend}
          disabled={disabled}
        />
      )}
    </div>
  )
}
