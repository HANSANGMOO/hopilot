import { HTMLAttributes, ReactNode } from 'react'

interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

export default function Container({ children, className = '', ...props }: ContainerProps) {
  return (
    <div className={`overflow-y-auto ${className}`} {...props}>
      {children}
    </div>
  )
}
