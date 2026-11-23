import { ReactNode, useState } from 'react'
import Block from '../atoms/Block'
import Header from '../atoms/Header'

type BlockVariant = 'default' | 'tool' | 'bare'
type BlockWidth   = 'full' | 'fit'
type HoverStyle   = 'bg' | 'bare'

interface ExpandableBlockProps {
  label: ReactNode
  children: ReactNode
  variant?:    BlockVariant
  width?:      BlockWidth
  showArrow?:  boolean
  hoverStyle?: HoverStyle
  defaultOpen?: boolean
  className?:  string
}

export default function ExpandableBlock({
  label,
  children,
  variant     = 'default',
  width       = 'full',
  showArrow   = true,
  hoverStyle  = 'bg',
  defaultOpen = false,
  className,
}: ExpandableBlockProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  const hoverClass = hoverStyle === 'bg' ? 'hover:bg-hover/30' : ''

  return (
    <Block variant={variant} width={width} className={className}>
      <button
        onClick={() => setIsOpen(prev => !prev)}
        className={`w-full text-left transition-colors ${hoverClass}`}
      >
        <Header
          label={label}
          right={showArrow ? (
            <span
              className="text-xs transition-transform duration-200"
              style={{ display: 'inline-block', transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)' }}
            >
              ▶
            </span>
          ) : undefined}
        />
      </button>
      {isOpen && (
        <div className="border-t border-border/50 px-4 py-3">
          {children}
        </div>
      )}
    </Block>
  )
}
