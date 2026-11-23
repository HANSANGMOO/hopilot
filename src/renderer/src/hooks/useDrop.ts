import { useState, useEffect, useRef } from 'react'

export function useDrop(onFiles: (files: File[]) => void) {
  const [dragActive, setDragActive] = useState(false)
  const counterRef = useRef(0)
  const onFilesRef = useRef(onFiles)
  onFilesRef.current = onFiles

  useEffect(() => {
    const onDragEnter = (e: DragEvent) => {
      e.preventDefault()
      counterRef.current += 1
      setDragActive(true)
    }

    const onDragLeave = (e: DragEvent) => {
      e.preventDefault()
      counterRef.current -= 1
      if (counterRef.current === 0) setDragActive(false)
    }

    const onDragOver = (e: DragEvent) => {
      e.preventDefault()
    }

    const onDrop = (e: DragEvent) => {
      e.preventDefault()
      counterRef.current = 0
      setDragActive(false)
      const files = e.dataTransfer ? Array.from(e.dataTransfer.files) : []
      if (files.length > 0) onFilesRef.current(files)
    }

    document.addEventListener('dragenter', onDragEnter)
    document.addEventListener('dragleave', onDragLeave)
    document.addEventListener('dragover', onDragOver)
    document.addEventListener('drop', onDrop)

    return () => {
      document.removeEventListener('dragenter', onDragEnter)
      document.removeEventListener('dragleave', onDragLeave)
      document.removeEventListener('dragover', onDragOver)
      document.removeEventListener('drop', onDrop)
    }
  }, [])

  return { dragActive }
}
