import { Send } from 'lucide-react'

interface ToolbarProps {
  input: string
  onSend: () => void
}

export default function Toolbar({ input, onSend }: ToolbarProps) {
  const disabled = !input.trim()

  return (
    <div className="mr-0.5 mb-0.5 flex shrink-0 items-center">
      <button
        onClick={onSend}
        disabled={disabled}
        className={`rounded-xl p-2.5 transition-colors ${
          !disabled
            ? 'bg-blue-600 text-white hover:bg-blue-500'
            : 'cursor-not-allowed bg-gray-800 text-gray-500'
        }`}
      >
        <Send size={18} className="ml-0.5" />
      </button>
    </div>
  )
}
