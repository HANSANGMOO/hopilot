import { useState } from 'react'
import { PanelLeftClose, PanelLeftOpen, Settings, MessageSquare } from 'lucide-react'

export default function Sidebar() {
  // 사이드바 내부에서 스스로 확장/축소 상태를 관리합니다. (기본값: false = 축소된 상태)
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <aside
      className={`flex flex-col border-r border-gray-800 bg-[#161b22] transition-all duration-300 ease-in-out ${
        isExpanded ? 'w-64' : 'w-[72px]'
      }`}
    >
      <div className="flex h-full flex-col overflow-hidden">
        {/* 상단 버튼 영역 */}
        <div
          className={`flex h-14 items-center border-b border-gray-800 p-4 ${isExpanded ? 'justify-between' : 'justify-center'}`}
        >
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="shrink-0 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-800 hover:text-white"
            title={isExpanded ? 'Close Sidebar' : 'Open Sidebar'}
          >
            {isExpanded ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
          </button>

          {isExpanded && (
            <h2 className="ml-3 flex-1 text-sm font-bold whitespace-nowrap text-gray-100">
              Hopilot
            </h2>
          )}
        </div>

        {/* 대화 목록 (스크롤 영역) */}
        <div className="flex flex-1 flex-col items-center space-y-2 overflow-y-auto p-3">
          <button
            className={`flex w-full items-center rounded-lg text-gray-300 transition-colors hover:bg-gray-800 ${
              isExpanded
                ? 'justify-start bg-gray-800/50 p-3'
                : 'justify-center p-3 hover:bg-gray-800'
            }`}
            title="두 번째 대화"
          >
            <MessageSquare size={20} className="shrink-0" />
            {isExpanded && <span className="ml-3 truncate text-sm">두 번째 대화</span>}
          </button>
        </div>

        {/* 하단 설정 영역 */}
        <div className="flex flex-col items-center border-t border-gray-800 p-3">
          <button
            className={`flex w-full items-center rounded-lg text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200 ${
              isExpanded ? 'justify-start p-3' : 'justify-center p-3'
            }`}
            title="Settings"
          >
            <Settings size={20} className="shrink-0" />
            {isExpanded && (
              <span className="ml-3 text-sm font-medium whitespace-nowrap">Settings</span>
            )}
          </button>
        </div>
      </div>
    </aside>
  )
}
