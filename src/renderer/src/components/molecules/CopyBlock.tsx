import { ReactNode, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import Block from '../atoms/Block'
import Header from '../atoms/Header'

interface CopyBlockProps {
  label?: string
  getText: () => string
  children: ReactNode
}

export default function CopyBlock({ label, getText, children }: CopyBlockProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(getText())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Block variant="default" className="my-4 shadow-sm">
      <Header
        label={<span className="text-text-tertiary">{label}</span>}
        right={
          <button onClick={handleCopy} className="flex items-center gap-1 text-text-tertiary hover:text-text-primary transition-colors">
            {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
          </button>
        }
        className="bg-elevated py-1.5"
      />
      <div>
        {children}
      </div>
    </Block>
  )
}
