import { useCallback, useEffect, useRef, useState } from 'react'
import { signalBus } from '../core/SignalBus'

export interface AskUserRequest {
  question: string
  choices?: string[] | null
  placeholder?: string
}

interface PendingRequest {
  id: string
  question: string
  choices?: string[] | null
  placeholder?: string
  resolve: (answer: string) => void
  reject: (err: Error) => void
}

export function useAskUser() {
  const [queue, setQueue] = useState<PendingRequest[]>([])
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const queueRef = useRef<PendingRequest[]>([])
  const answersRef = useRef<Record<string, string>>({})

  useEffect(() => {
    const disposable = signalBus.requests.handle<AskUserRequest, { answer: string }>(
      'tool/ask_user',
      (params) =>
        new Promise((resolve, reject) => {
          const request: PendingRequest = {
            id: crypto.randomUUID(),
            question: params.question,
            choices: params.choices,
            placeholder: params.placeholder,
            resolve: (answer) => resolve({ answer }),
            reject,
          }
          queueRef.current = [...queueRef.current, request]
          setQueue(queueRef.current)
        })
    )
    return () => disposable.dispose()
  }, [])

  const resetBatch = useCallback(() => {
    queueRef.current = []
    answersRef.current = {}
    setQueue([])
    setAnswers({})
    setIndex(0)
  }, [])

  const setAnswer = useCallback((value: string) => {
    const request = queueRef.current[index]
    if (!request) return
    answersRef.current = { ...answersRef.current, [request.id]: value }
    setAnswers(answersRef.current)
  }, [index])

  const back = useCallback(() => {
    setIndex(i => Math.max(0, i - 1))
  }, [])

  const advance = useCallback(() => {
    if (index >= queueRef.current.length - 1) {
      const requests = queueRef.current
      const finalAnswers = answersRef.current
      requests.forEach(r => r.resolve(finalAnswers[r.id] ?? ''))
      resetBatch()
    } else {
      setIndex(index + 1)
    }
  }, [index, resetBatch])

  const selectChoice = useCallback((value: string) => {
    setAnswer(value)
    advance()
  }, [setAnswer, advance])

  const cancel = useCallback(() => {
    queueRef.current.forEach(r => r.reject(new Error('User cancelled')))
    resetBatch()
  }, [resetBatch])

  const current = queue[index] ?? null
  const total = queue.length

  return {
    isOpen: current !== null,
    question: current?.question ?? '',
    choices: current?.choices ?? null,
    placeholder: current?.placeholder,
    answer: current ? (answers[current.id] ?? '') : '',
    index,
    total,
    isFirst: index === 0,
    isLast: index >= total - 1,
    setAnswer,
    back,
    advance,
    selectChoice,
    cancel,
  }
}
