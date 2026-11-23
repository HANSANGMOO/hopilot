import CodeBlock from './CodeBlock'

interface CodeToolContentProps {
  args: object
  output: string
}

function parseOutput(output: string): { stdout?: string; stderr?: string; plain: string } {
  const stdoutMatch = output.match(/--- Stdout ---\n([\s\S]*?)(?=\n\n--- Stderr ---|$)/)
  const stderrMatch = output.match(/--- Stderr ---\n([\s\S]*)$/)
  if (!stdoutMatch && !stderrMatch) return { plain: output }
  return {
    stdout: stdoutMatch?.[1]?.trim(),
    stderr: stderrMatch?.[1]?.trim(),
    plain: output,
  }
}

export default function CodeToolContent({ args, output }: CodeToolContentProps) {
  const a = args as Record<string, string>
  const { stdout, stderr, plain } = parseOutput(output)
  const hasStructured = stdout !== undefined || stderr !== undefined

  return (
    <div className="flex flex-col gap-2 pt-1">
      {a.code && (
        <CodeBlock code={a.code} language="python" label="Input" />
      )}
      {output && (hasStructured ? (
        <>
          {stdout && <CodeBlock code={stdout} language="text" label="stdout" />}
          {stderr && <CodeBlock code={stderr} language="text" label="stderr" />}
        </>
      ) : (
        <CodeBlock code={plain} language="text" label="Output" />
      ))}
    </div>
  )
}
