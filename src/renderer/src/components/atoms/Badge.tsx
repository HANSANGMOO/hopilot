import { ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

const badgeVariants = cva(
  'inline-flex items-center rounded-full font-medium',
  {
    variants: {
      variant: {
        default:  'bg-border text-text-secondary',
        primary:  'bg-blue-600/20 text-blue-400',
        success:  'bg-green-600/20 text-green-400',
        warning:  'bg-yellow-600/20 text-yellow-400',
        danger:   'bg-red-600/20 text-red-400',
      },
      size: {
        sm: 'px-2 py-0.5 text-xs',
        md: 'px-2.5 py-1 text-sm',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'sm',
    },
  }
)

interface BadgeProps extends VariantProps<typeof badgeVariants> {
  children: ReactNode
}

export default function Badge({ children, variant, size }: BadgeProps) {
  return (
    <span className={badgeVariants({ variant, size })}>
      {children}
    </span>
  )
}
