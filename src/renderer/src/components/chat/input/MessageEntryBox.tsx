interface MessageEntryBoxProps {
  input: string
  setInput: (value: string) => void
  onSend: () => void
}

export default function MessageEntryBox({ input, setInput, onSend }: MessageEntryBoxProps) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <textarea
      placeholder="Hopilot에게 무엇이든 물어보세요..."
      className="max-h-48 min-h-[44px] flex-1 resize-none bg-transparent px-3 py-2 text-gray-200 placeholder-gray-500 outline-none"
      rows={1}
      value={input}
      onChange={(e) => setInput(e.target.value)}
      onKeyDown={handleKeyDown}
    />
  )
}
