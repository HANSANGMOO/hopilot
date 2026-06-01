import { Bot, User } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Message } from '../../types/chat'
import { cva, type VariantProps } from 'class-variance-authority'

const containerVariants = cva('flex w-full', {
  variants: {
    role: {
      user: 'flex-row-reverse gap-4',
      ai: 'flex-col gap-2'
    },
    size: {
      small: '',
      normal: ''
    }
  },
  defaultVariants: {
    role: 'user',
    size: 'normal'
  }
})

const avatarVariants = cva('rounded-full flex items-center justify-center shrink-0', {
  variants: {
    role: {
      user: 'bg-blue-600 text-white mt-1',
      ai: 'bg-gray-800 text-blue-400'
    },
    size: {
      small: 'w-6 h-6',
      normal: 'w-8 h-8'
    }
  },
  defaultVariants: {
    role: 'user',
    size: 'normal'
  }
})

const bubbleVariants = cva('leading-relaxed rounded-2xl max-w-full', {
  variants: {
    role: {
      user: 'bg-blue-600 text-white rounded-tr-sm px-5 py-3.5 lg:max-w-[85%]',
      ai: 'bg-transparent text-gray-200 w-full py-1'
    },
    size: {
      small: 'text-sm',
      normal: 'text-base'
    }
  },
  defaultVariants: {
    role: 'user',
    size: 'normal'
  }
})

interface MessageBubbleProps {
  message: Message
  size?: VariantProps<typeof bubbleVariants>['size']
}

export default function MessageBubble({ message, size = 'normal' }: MessageBubbleProps) {
  // message.role 타입 보장
  const role = message.role === 'user' ? 'user' : 'ai'

  return (
    <div className={containerVariants({ role, size })}>
      {role === 'ai' && (
        <div className="flex items-center gap-3">
          <div className={avatarVariants({ role, size })}>
            <Bot size={size === 'small' ? 14 : 18} />
          </div>
          <span className="font-semibold text-gray-300">Hopilot</span>
        </div>
      )}

      {role === 'user' && (
        <div className={avatarVariants({ role, size })}>
          <User size={size === 'small' ? 14 : 18} />
        </div>
      )}

      <div className={bubbleVariants({ role, size })}>
        {role === 'user' ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div
            className={`prose prose-invert max-w-none leading-relaxed text-gray-200 ${size === 'small' ? 'text-sm' : 'text-base'}`}
          >
            <ReactMarkdown
              components={{
                code(props: any) {
                  const { children, className, node, ref, ...rest } = props
                  const match = /language-(\w+)/.exec(className || '')

                  return match ? (
                    <div className="my-4 overflow-hidden rounded-lg border border-gray-700 shadow-sm">
                      <div className="flex items-center justify-between bg-gray-800 px-4 py-1.5 text-xs text-gray-400">
                        <span>{match[1]}</span>
                      </div>
                      <SyntaxHighlighter
                        {...rest}
                        PreTag="div"
                        children={String(children).replace(/\n$/, '')}
                        language={match[1]}
                        style={vscDarkPlus}
                        customStyle={{
                          margin: 0,
                          borderRadius: 0,
                          background: '#161b22',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>
                  ) : (
                    <code
                      ref={ref}
                      {...rest}
                      className="rounded bg-gray-800 px-1.5 py-0.5 font-mono text-sm text-pink-400"
                    >
                      {children}
                    </code>
                  )
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
