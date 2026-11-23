import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import CodeBlock from '../components/molecules/CodeBlock'
import 'katex/dist/katex.min.css'

function CodeRenderer({ children, className }: any) {
  const match = /language-(\w+)/.exec(className || '')
  const code = String(children).replace(/\n$/, '')

  return match ? (
    <CodeBlock code={code} language={match[1]} />
  ) : (
    <code className="rounded bg-elevated px-1.5 py-0.5 font-mono text-sm text-[var(--color-inline-code)] whitespace-pre-wrap">
      {children}
    </code>
  )
}

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const rendered = useMemo(() => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{ code: CodeRenderer, pre: ({ children }) => <>{children}</> }}
    >
      {content}
    </ReactMarkdown>
  ), [content])

  return (
    <div className="prose max-w-none prose-strong:font-bold prose-code:before:content-none prose-code:after:content-none [&_.katex-display]:text-center [&_.katex-display]:my-4 prose-p:text-text-primary prose-headings:text-text-primary prose-strong:text-text-primary prose-li:text-text-primary prose-a:text-blue-500 prose-blockquote:text-text-secondary prose-code:text-[var(--color-inline-code)]">
      {rendered}
    </div>
  )
}
