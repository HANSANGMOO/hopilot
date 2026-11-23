import { useEffect, useRef, useState } from 'react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { MoreHorizontal, Trash2, Pencil, FolderInput, FolderMinus, ChevronRight } from 'lucide-react'
import IconButton from '../../atoms/IconButton'
import { Project } from '../../../types/project'
import { dropdownContent, dropdownItem, dropdownItemDanger, dropdownSubTrigger, dropdownSeparator } from '../../../styles/dropdown'

interface SessionItemProps {
  title: string
  date: string
  isActive?: boolean
  isStreaming?: boolean
  projectId?: string
  projects?: Project[]
  onSelect: () => void
  onDelete: () => void
  onRename: (newTitle: string) => void
  onMoveToProject?: (projectId: string | null) => void
}

interface SessionItemMenuProps {
  projectId?: string
  projects: Project[]
  onRename: () => void
  onDelete: () => void
  onMoveToProject?: (projectId: string | null) => void
}

function SessionItemMenu({ projectId, projects, onRename, onDelete, onMoveToProject }: SessionItemMenuProps) {
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <IconButton icon={<MoreHorizontal size={14} />} label="더보기" variant="ghost" size="sm" />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content className={dropdownContent} align="end" sideOffset={4}>
          <DropdownMenu.Item className={dropdownItem} onSelect={onRename}>
            <Pencil size={13} />
            이름 바꾸기
          </DropdownMenu.Item>
          {onMoveToProject && (
            <DropdownMenu.Sub>
              <DropdownMenu.SubTrigger className={dropdownSubTrigger}>
                <FolderInput size={13} />
                <span className="flex-1 text-left">프로젝트로 이동</span>
                <ChevronRight size={12} className="ml-auto text-icon" />
              </DropdownMenu.SubTrigger>
              <DropdownMenu.Portal>
                <DropdownMenu.SubContent className={dropdownContent} sideOffset={4} alignOffset={-6}>
                  {projects.map(p => (
                    <DropdownMenu.Item key={p.id} className={dropdownItem} onSelect={() => onMoveToProject(p.id)}>
                      {p.id === projectId && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />}
                      {p.name}
                    </DropdownMenu.Item>
                  ))}
                  {projectId && (
                    <>
                      {projects.length > 0 && <DropdownMenu.Separator className={dropdownSeparator} />}
                      <DropdownMenu.Item className={dropdownItem} onSelect={() => onMoveToProject(null)}>
                        <FolderMinus size={13} />
                        프로젝트 해제
                      </DropdownMenu.Item>
                    </>
                  )}
                </DropdownMenu.SubContent>
              </DropdownMenu.Portal>
            </DropdownMenu.Sub>
          )}
          <DropdownMenu.Separator className={dropdownSeparator} />
          <DropdownMenu.Item className={dropdownItemDanger} onSelect={onDelete}>
            <Trash2 size={13} />
            삭제
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}

export default function SessionItem({ title, date, isActive, isStreaming, projectId, projects = [], onSelect, onDelete, onRename, onMoveToProject }: SessionItemProps) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState(title)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) {
      setEditValue(title)
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing, title])

  const commitEdit = () => {
    const trimmed = editValue.trim()
    if (trimmed && trimmed !== title) onRename(trimmed)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className={`relative flex items-center rounded-lg px-3 py-2 ${isActive ? 'bg-blue-600/10' : 'bg-elevated'}`}>
        <input
          ref={inputRef}
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false) }}
          onBlur={commitEdit}
          onClick={e => e.stopPropagation()}
          className="w-full bg-transparent text-sm font-medium text-text-primary outline-none"
        />
      </div>
    )
  }

  return (
    <div
      onClick={onSelect}
      className={`group relative flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 transition-colors ${
        isActive ? 'bg-[var(--color-session-active)] text-text-primary' : 'text-text-secondary hover:bg-hover'
      }`}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="truncate text-sm font-medium">{title}</span>
          {isStreaming && <span className="shrink-0 w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />}
        </div>
        <span className="text-xs text-text-muted">{date}</span>
      </div>

      <div className="ml-2 opacity-0 transition-opacity group-hover:opacity-100" onClick={e => e.stopPropagation()}>
        <SessionItemMenu
          projectId={projectId}
          projects={projects}
          onRename={() => setEditing(true)}
          onDelete={onDelete}
          onMoveToProject={onMoveToProject}
        />
      </div>
    </div>
  )
}
