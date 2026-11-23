import { useEffect, useRef, useState } from 'react'
import * as Collapsible from '@radix-ui/react-collapsible'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { ChevronRight, FolderOpen, MoreHorizontal, Trash2, Pencil, Plus, FolderCog } from 'lucide-react'
import { Session } from '../../../types/session'
import { Project } from '../../../types/project'
import IconButton from '../../atoms/IconButton'
import SessionItem from './SessionItem'
import { formatDate } from './formatDate'
import { useSessionContext } from '../../../contexts/SessionContext'
import { dropdownContent, dropdownItem, dropdownItemDanger, dropdownSeparator } from '../../../styles/dropdown'

interface ProjectGroupHeaderProps {
  project: Project
  onCreateSession: () => void
  onSetWorkspace: () => void
  onRename: (newName: string) => void
  onDelete: () => void
}

function ProjectGroupHeader({ project, onCreateSession, onSetWorkspace, onRename, onDelete }: ProjectGroupHeaderProps) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState(project.name)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (editing) {
      setEditValue(project.name)
      inputRef.current?.focus()
      inputRef.current?.select()
    }
  }, [editing, project.name])

  const commitEdit = () => {
    const trimmed = editValue.trim()
    if (trimmed && trimmed !== project.name) onRename(trimmed)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="flex items-center gap-1.5 px-1 py-1">
        <FolderOpen size={13} className="shrink-0 text-text-tertiary" />
        <input
          ref={inputRef}
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false) }}
          onBlur={commitEdit}
          onClick={e => e.stopPropagation()}
          className="w-full bg-transparent text-xs font-semibold text-text-secondary outline-none"
        />
      </div>
    )
  }

  return (
    <div className="group flex items-center justify-between px-1 py-1">
      <div className="flex flex-col min-w-0 gap-0.5">
        <div className="flex items-center gap-1.5">
          <FolderOpen size={13} className="shrink-0 text-text-tertiary" />
          <span className="truncate text-xs font-semibold text-text-tertiary uppercase tracking-wider">{project.name}</span>
        </div>
        <span className="truncate text-xs text-text-faint pl-5">{project.workspace}</span>
      </div>
      <div className="opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <IconButton icon={<MoreHorizontal size={13} />} label="프로젝트 더보기" variant="ghost" size="sm" />
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className={dropdownContent} align="end" sideOffset={4}>
              <DropdownMenu.Item className={dropdownItem} onSelect={onCreateSession}>
                <Plus size={13} />
                세션 추가
              </DropdownMenu.Item>
              <DropdownMenu.Item className={dropdownItem} onSelect={onSetWorkspace}>
                <FolderCog size={13} />
                작업폴더 설정
              </DropdownMenu.Item>
              <DropdownMenu.Item className={dropdownItem} onSelect={() => setEditing(true)}>
                <Pencil size={13} />
                이름 바꾸기
              </DropdownMenu.Item>
              <DropdownMenu.Separator className={dropdownSeparator} />
              <DropdownMenu.Item className={dropdownItemDanger} onSelect={onDelete}>
                <Trash2 size={13} />
                삭제
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </div>
  )
}

interface ProjectGroupProps {
  project: Project
  sessions: Session[]
  projects: Project[]
  activeId?: string
  onSelect: (id: string) => void
  onDelete: (id: string) => void
  onRename: (id: string, newTitle: string) => void
  onMoveToProject: (id: string, projectId: string | null) => void
  onCreateSession: () => void
  onSetWorkspace: () => void
  onRenameProject: (newName: string) => void
  onDeleteProject: () => void
}

export default function ProjectGroup({
  project,
  sessions,
  projects,
  activeId,
  onSelect,
  onDelete,
  onRename,
  onMoveToProject,
  onCreateSession,
  onSetWorkspace,
  onRenameProject,
  onDeleteProject,
}: ProjectGroupProps) {
  const { streamingSessions } = useSessionContext()
  const [open, setOpen] = useState(false)

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen}>
      <div className="flex items-center cursor-pointer" onClick={() => setOpen(prev => !prev)}>
        <ChevronRight
          size={12}
          className={`mr-1 shrink-0 text-text-muted transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <div className="flex-1 min-w-0">
          <ProjectGroupHeader
            project={project}
            onCreateSession={onCreateSession}
            onSetWorkspace={onSetWorkspace}
            onRename={onRenameProject}
            onDelete={onDeleteProject}
          />
        </div>
      </div>
      <Collapsible.Content className="overflow-hidden data-[state=open]:animate-slideDown data-[state=closed]:animate-slideUp">
        <div className="flex flex-col gap-1 pl-2 mt-1">
          {sessions.length === 0 ? (
            <p className="px-3 text-xs text-text-faint">세션 없음</p>
          ) : (
            sessions.map(session => (
              <SessionItem
                key={session.id}
                title={session.title}
                date={formatDate(session.updatedAt)}
                isActive={session.id === activeId}
                isStreaming={streamingSessions.get(session.id) ?? false}
                projectId={session.projectId}
                projects={projects}
                onSelect={() => onSelect(session.id)}
                onDelete={() => onDelete(session.id)}
                onRename={(newTitle) => onRename(session.id, newTitle)}
                onMoveToProject={(projectId) => onMoveToProject(session.id, projectId)}
              />
            ))
          )}
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  )
}
