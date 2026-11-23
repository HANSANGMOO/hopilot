import { useState } from 'react'
import { Home, Plus, Settings, PanelLeftClose, PanelLeftOpen, FolderPlus } from 'lucide-react'
import { Session } from '../../../types/session'
import { Project } from '../../../types/project'
import IconButton from '../../atoms/IconButton'
import Button from '../../atoms/Button'
import ProjectGroup from './ProjectGroup'
import SessionItem from './SessionItem'
import { formatDate } from './formatDate'
import { useSessionContext } from '../../../contexts/SessionContext'

interface NavPanelProps {
  sessions: Session[]
  activeSessionId?: string
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
  onRenameSession: (id: string, newTitle: string) => void
  onCreateSession: () => void
  projects: Project[]
  onDeleteProject: (id: string) => void
  onRenameProject: (id: string, newName: string) => void
  onCreateProject: () => void
  onCreateSessionInProject: (id: string) => void
  onMoveToProject: (sessionId: string, projectId: string | null) => void
  onSetWorkspace: (projectId: string) => void
  onHome: () => void
  onSettings: () => void
}

export default function NavPanel({
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onRenameSession,
  onCreateSession,
  projects,
  onDeleteProject,
  onRenameProject,
  onCreateProject,
  onCreateSessionInProject,
  onMoveToProject,
  onSetWorkspace,
  onHome,
  onSettings,
}: NavPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const { streamingSessions } = useSessionContext()

  const defaultSessions = sessions.filter(s => !s.projectId)
  const projectGroups = projects.map(p => ({
    project: p,
    sessions: sessions.filter(s => s.projectId === p.id),
  }))

  return (
    <aside
      className={`flex flex-col h-full overflow-hidden border-r border-border-strong bg-surface transition-all duration-300 ease-in-out ${
        isExpanded ? 'w-64' : 'w-[56px]'
      }`}
    >
      {/* 토글 헤더 */}
      <div className="flex h-12 shrink-0 items-center border-b border-border-strong px-3">
        <IconButton
          icon={isExpanded ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          label={isExpanded ? '패널 닫기' : '패널 열기'}
          onClick={() => setIsExpanded(prev => !prev)}
        />
      </div>

      {/* 액션 버튼 */}
      <div className={`shrink-0 flex flex-col gap-1 p-2 border-b border-border-strong ${!isExpanded && 'items-center'}`}>
        {isExpanded ? (
          <>
            <Button
              variant="ghost"
              size="md"
              leftIcon={<Plus size={16} />}
              className="w-full justify-start"
              onClick={onCreateSession}
            >
              새 세션
            </Button>
            <Button
              variant="ghost"
              size="md"
              leftIcon={<FolderPlus size={16} />}
              className="w-full justify-start"
              onClick={onCreateProject}
            >
              새 프로젝트
            </Button>
          </>
        ) : (
          <>
            <IconButton icon={<Plus size={18} />} label="새 세션" onClick={onCreateSession} />
            <IconButton icon={<FolderPlus size={18} />} label="새 프로젝트" onClick={onCreateProject} />
          </>
        )}
      </div>

      {/* 세션/프로젝트 목록 - 펼쳤을 때만, 접혔을 때는 spacer로 대체 */}
      {isExpanded ? (
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <div className="flex flex-col gap-3">
            <div className="px-1 py-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">프로젝트 목록</span>
            </div>
            {projectGroups.length === 0 && (
              <p className="px-3 text-xs text-text-muted">프로젝트가 없습니다.</p>
            )}
            {projectGroups.map(({ project, sessions: groupSessions }) => (
              <ProjectGroup
                key={project.id}
                project={project}
                sessions={groupSessions}
                projects={projects}
                activeId={activeSessionId}
                onSelect={onSelectSession}
                onDelete={onDeleteSession}
                onRename={onRenameSession}
                onMoveToProject={onMoveToProject}
                onCreateSession={() => onCreateSessionInProject(project.id)}
                onSetWorkspace={() => onSetWorkspace(project.id)}
                onRenameProject={(newName) => onRenameProject(project.id, newName)}
                onDeleteProject={() => onDeleteProject(project.id)}
              />
            ))}

            <div className="border-t border-border-strong" />

            <div>
              <div className="px-1 py-1 mb-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">기본 세션 목록</span>
              </div>
              {defaultSessions.length === 0 ? (
                <p className="px-3 text-xs text-text-muted">세션이 없습니다.</p>
              ) : (
                <div className="flex flex-col gap-1">
                  {defaultSessions.map(session => (
                    <SessionItem
                      key={session.id}
                      title={session.title}
                      date={formatDate(session.updatedAt)}
                      isActive={session.id === activeSessionId}
                      isStreaming={streamingSessions.get(session.id) ?? false}
                      projects={projects}
                      onSelect={() => onSelectSession(session.id)}
                      onDelete={() => onDeleteSession(session.id)}
                      onRename={(newTitle) => onRenameSession(session.id, newTitle)}
                      onMoveToProject={(projectId) => onMoveToProject(session.id, projectId)}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1" />
      )}

      {/* 푸터 */}
      <div className={`shrink-0 flex items-center border-t border-border-strong p-3 ${isExpanded ? 'justify-between' : 'justify-center'}`}>
        {isExpanded && <IconButton icon={<Home size={18} />} label="홈" onClick={onHome} />}
        <IconButton icon={<Settings size={18} />} label="설정" onClick={onSettings} />
      </div>
    </aside>
  )
}
