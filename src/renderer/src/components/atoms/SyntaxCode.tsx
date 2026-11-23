import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useTheme } from '../../contexts/ThemeContext'

interface SyntaxCodeProps {
  code: string
  language?: string
}

export default function SyntaxCode({ code, language = 'text' }: SyntaxCodeProps) {
  const { theme } = useTheme()

  return (
    <SyntaxHighlighter
      PreTag="div"
      language={language}
      style={theme === 'dark' ? vscDarkPlus : vs}
      customStyle={{
        margin: 0,
        borderRadius: 0,
        background: 'var(--color-syntax)',
        fontSize: '0.9rem',
        fontFamily: "'Consolas', 'Courier New', monospace",
        lineHeight: '1.6',
      }}
      codeTagProps={{
        style: { whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontWeight: 400 },
      }}
    >
      {code}
    </SyntaxHighlighter>
  )
}
