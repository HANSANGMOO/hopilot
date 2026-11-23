import { cva, type VariantProps } from 'class-variance-authority'

const spinnerVariants = cva(
  'rounded-full border-2 border-border-input border-t-text-secondary animate-spin shrink-0',
  {
    variants: {
      size: {
        sm: 'w-3 h-3',
        md: 'w-4 h-4',
        lg: 'w-5 h-5',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
)

interface SpinnerProps extends VariantProps<typeof spinnerVariants> {
  className?: string
}

export default function Spinner({ size, className }: SpinnerProps) {
  return <div className={spinnerVariants({ size, className })} />
}
