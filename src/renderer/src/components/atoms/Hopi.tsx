import { useState, useEffect } from 'react'

export default function Hopi() {
  const [floatY, setFloatY] = useState(0)
  const [isBlinking, setIsBlinking] = useState(false)

  useEffect(() => {
    let animationFrameId: number
    const start = Date.now()
    const animate = () => {
      setFloatY(Math.sin((Date.now() - start) / 600) * 6)
      animationFrameId = requestAnimationFrame(animate)
    }
    animate()
    return () => cancelAnimationFrame(animationFrameId)
  }, [])

  useEffect(() => {
    let timeoutId: NodeJS.Timeout
    const blink = () => {
      setIsBlinking(true)
      setTimeout(() => setIsBlinking(false), 150)
      timeoutId = setTimeout(blink, Math.random() * 4000 + 2000)
    }
    timeoutId = setTimeout(blink, 2000)
    return () => clearTimeout(timeoutId)
  }, [])

  return (
    <div style={{ transform: `translateY(${floatY}px)` }}>
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-hopi-bg border border-border shadow-md">
        <div className="flex space-x-4">
          <div className={`w-2.5 bg-hopi-eye rounded-xl transition-all duration-200 ${isBlinking ? 'h-0.5' : 'h-2.5'}`} />
          <div className={`w-2.5 bg-hopi-eye rounded-xl transition-all duration-200 ${isBlinking ? 'h-0.5' : 'h-2.5'}`} />
        </div>
      </div>
    </div>
  )
}
