import { ButtonHTMLAttributes, ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

const iconButtonVariants = cva(
  'inline-flex items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'text-icon hover:bg-hover hover:text-text-primary',
        primary: 'bg-[var(--color-brand)] text-[var(--color-brand-text)] hover:opacity-90',
        ghost:   'text-icon hover:text-text-primary',
        danger:  'text-icon hover:bg-red-900/30 hover:text-red-400',
      },
      size: {
        sm: 'p-1.5',
        md: 'p-2',
        lg: 'p-2.5',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  }
)

interface IconButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof iconButtonVariants> {
  icon: ReactNode
  label: string   // 접근성용 aria-label
}

export default function IconButton({ icon, label, variant, size, className, ...props }: IconButtonProps) {
  return (
    <button
      aria-label={label}
      title={label}
      className={iconButtonVariants({ variant, size, className })}
      {...props}
    >
      {icon}
    </button>
  )
}
