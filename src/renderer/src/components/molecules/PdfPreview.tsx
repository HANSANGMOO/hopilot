import { useEffect, useMemo, useState } from 'react'
import { Loader2 } from 'lucide-react'

interface PdfPreviewProps {
  data: string  // base64
  className?: string
}

export default function PdfPreview({ data, className = 'h-full w-full' }: PdfPreviewProps) {
  const [loaded, setLoaded] = useState(false)

  const blobUrl = useMemo(() => {
    const binary = atob(data)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: 'application/pdf' })
    return URL.createObjectURL(blob)
  }, [data])

  useEffect(() => {
    setLoaded(false)
    return () => URL.revokeObjectURL(blobUrl)
  }, [blobUrl])

  return (
    <div className="relative h-full w-full">
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center">
          <Loader2 size={18} className="animate-spin text-text-muted" />
        </div>
      )}
      <iframe src={blobUrl} className={className} onLoad={() => setLoaded(true)} />
    </div>
  )
}
