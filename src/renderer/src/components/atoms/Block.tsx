import { HTMLAttributes, ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

const blockVariants = cva(
  'rounded-lg overflow-hidden',
  {
    variants: {
      variant: {
        default: 'border border-border/50 bg-[var(--color-block-default-bg)]',
        tool:    'border border-[var(--color-block-tool-border)] bg-[var(--color-block-tool-bg)]',
        bare:    '',
      },
      padding: {
        none: '',
        sm:   'px-3 py-2',
        md:   'px-4 py-3',
      },
      width: {
        full: 'w-full',
        fit:  'w-fit',
      },
    },
    defaultVariants: {
      variant: 'default',
      padding: 'none',
      width:   'full',
    },
  }
)

interface BlockProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof blockVariants> {
  children: ReactNode
}

export default function Block({ children, variant, padding, width, className, ...props }: BlockProps) {
  return (
    <div className={blockVariants({ variant, padding, width, className })} {...props}>
      {children}
    </div>
  )
}
