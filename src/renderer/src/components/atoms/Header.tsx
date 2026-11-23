import { HTMLAttributes, ReactNode } from 'react'

interface HeaderProps extends HTMLAttributes<HTMLDivElement> {
  label: ReactNode
  right?: ReactNode
}

export default function Header({ label, right, className, ...props }: HeaderProps) {
  return (
    <div className={`flex items-center justify-between px-4 py-2.5 ${className ?? ''}`} {...props}>
      <span className="text-sm">{label}</span>
      {right && <span className="shrink-0">{right}</span>}
    </div>
  )
}
