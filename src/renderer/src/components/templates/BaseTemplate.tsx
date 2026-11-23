import { ReactNode } from 'react'

interface BaseTemplateProps {
  leftPanel: ReactNode
  rightPanel: ReactNode
  header: ReactNode
  body: ReactNode
  footer: ReactNode
}

export default function BaseTemplate({
  leftPanel,
  rightPanel,
  header,
  body,
  footer,
}: BaseTemplateProps) {
  return (
    <div className="flex h-screen w-full bg-base font-sans text-text-primary">

      {/* 좌측 패널 */}
      {leftPanel}

      {/* 메인 영역 */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="shrink-0">{header}</div>
        <div className="flex-1 overflow-hidden ml-1 mr-1">{body}</div>
        <div className="shrink-0">{footer}</div>
      </main>

      {/* 우측 패널 */}
      {rightPanel}

    </div>
  )
}
