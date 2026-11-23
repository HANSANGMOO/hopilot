import { ButtonHTMLAttributes, ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

const buttonVariants = cva(
  'inline-flex items-center gap-2 rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        primary:   'bg-[var(--color-brand)] text-[var(--color-brand-text)] hover:opacity-90',
        secondary: 'bg-elevated text-text-primary hover:bg-hover',
        ghost:     'text-icon hover:bg-hover hover:text-text-primary',
        danger:    'bg-red-700 text-white hover:bg-red-600',
      },
      size: {
        sm: 'px-2.5 py-1.5 text-xs',
        md: 'px-3 py-2 text-sm',
        lg: 'px-4 py-2.5 text-base',
      },
    },
    defaultVariants: {
      variant: 'ghost',
      size: 'md',
    },
  }
)

interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  children: ReactNode
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

export default function Button({ children, variant, size, leftIcon, rightIcon, className, ...props }: ButtonProps) {
  return (
    <button className={buttonVariants({ variant, size, className })} {...props}>
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  )
}
