import MessageEntryBox from './MessageEntryBox'
import Toolbar from './Toolbar'
import ModelSelector from './ModelSelector'

interface ChatInputProps {
  input: string
  setInput: (value: string) => void
  onSend: () => void
}

export default function ChatInput({ input, setInput, onSend }: ChatInputProps) {
  return (
    <div className="absolute bottom-0 w-full bg-gradient-to-t from-[#0d1117] via-[#0d1117] to-transparent p-6">
      <div className="mx-auto max-w-3xl">
        {/* 전체 입력 박스 */}
        <div className="relative flex flex-col rounded-2xl border border-gray-700 bg-[#161b22] p-2 shadow-xl transition-all focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/50">
          
          {/* 상단: 텍스트 입력부 */}
          <MessageEntryBox input={input} setInput={setInput} onSend={onSend} />
          
          {/* 하단: 툴바 및 모델 선택기 */}
          <div className="mt-1 flex items-center justify-between px-1">
            <ModelSelector />
            <Toolbar input={input} onSend={onSend} />
          </div>
        </div>
        
        <div className="mt-3 text-center text-xs text-gray-500">
          Hopilot은 실수를 할 수 있습니다. 중요한 코드는 직접 확인하세요.
        </div>
      </div>
    </div>
  )
}
