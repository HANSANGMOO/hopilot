import TextareaAutosize from 'react-textarea-autosize'

const MAX_ROWS = 5

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  onSubmit?: () => void
  expanded?: boolean
  onHeightChange?: (height: number) => void
}

export default function TextArea({ onSubmit, className, expanded, onHeightChange, style: _style, ...props }: TextAreaProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && onSubmit) {
      e.preventDefault()
      onSubmit()
    }
    props.onKeyDown?.(e)
  }

  return (
    <TextareaAutosize
      minRows={1}
      maxRows={expanded ? undefined : MAX_ROWS}
      className={`w-full resize-none bg-transparent text-text-primary placeholder-text-muted outline-none ${className ?? ''}`}
      onKeyDown={handleKeyDown}
      onHeightChange={onHeightChange}
      {...props}
    />
  )
}
