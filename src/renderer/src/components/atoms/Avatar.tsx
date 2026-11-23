import { Bot, User } from 'lucide-react'
import { cva, type VariantProps } from 'class-variance-authority'

const avatarVariants = cva(
  'rounded-full flex items-center justify-center shrink-0',
  {
    variants: {
      role: {
        user: 'bg-[var(--color-brand)] text-[var(--color-brand-text)]',
        ai:   'bg-elevated text-icon',
      },
      size: {
        sm: 'w-6 h-6',
        md: 'w-8 h-8',
      },
    },
    defaultVariants: {
      role: 'user',
      size: 'md',
    },
  }
)

interface AvatarProps extends VariantProps<typeof avatarVariants> {}

export default function Avatar({ role = 'user', size = 'md' }: AvatarProps) {
  const iconSize = size === 'sm' ? 14 : 18

  return (
    <div className={avatarVariants({ role, size })}>
      {role === 'user' ? <User size={iconSize} /> : <Bot size={iconSize} />}
    </div>
  )
}
