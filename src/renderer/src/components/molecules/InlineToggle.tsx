import { ReactNode, useState } from 'react'

interface InlineToggleProps {
  label: ReactNode
  children: ReactNode
  defaultOpen?: boolean
}

export default function InlineToggle({ label, children, defaultOpen = false }: InlineToggleProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div>
      <button onClick={() => setIsOpen(prev => !prev)} className="text-left">
        {label}
      </button>
      {isOpen && (
        <div className="mt-1 pl-1">
          {children}
        </div>
      )}
    </div>
  )
}
