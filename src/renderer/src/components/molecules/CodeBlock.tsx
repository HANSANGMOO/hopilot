import CopyBlock from './CopyBlock'
import SyntaxCode from '../atoms/SyntaxCode'

interface CodeBlockProps {
  code: string
  language?: string
  label?: string
}

export default function CodeBlock({ code, language = 'text', label }: CodeBlockProps) {
  return (
    <CopyBlock label={label ?? language} getText={() => code}>
      <SyntaxCode code={code} language={language} />
    </CopyBlock>
  )
}
