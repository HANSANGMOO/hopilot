import { ChevronDown } from 'lucide-react'

export default function ModelSelector() {
  return (
    <button className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200">
      <span>Gemini 1.5 Pro</span>
      <ChevronDown size={14} />
    </button>
  )
}
