import MessageEntryBox from './MessageEntryBox'
import Toolbar from './Toolbar'

interface ChatInputProps {
  input: string
  setInput: (value: string) => void
  onSend: () => void
}

export default function ChatInput({ input, setInput, onSend }: ChatInputProps) {
  return (
    <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#0d1117] via-[#0d1117] to-transparent p-6">
      <div className="mx-auto max-w-3xl">
        <div className="relative flex items-end rounded-2xl border border-gray-700 bg-[#161b22] p-2 shadow-xl transition-all focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/50">
          <MessageEntryBox input={input} setInput={setInput} onSend={onSend} />
          <Toolbar input={input} onSend={onSend} />
        </div>
        <div className="mt-3 text-center text-xs text-gray-500">
          Hopilot은 실수를 할 수 있습니다. 중요한 코드는 직접 확인하세요.
        </div>
      </div>
    </div>
  )
}
