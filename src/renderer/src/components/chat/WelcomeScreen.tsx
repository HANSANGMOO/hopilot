import { useState, useEffect } from 'react'

export default function WelcomeScreen() {
  const [floatY, setFloatY] = useState(0)
  const [isBlinking, setIsBlinking] = useState(false)

  // 부드럽고 잔잔한 상하 둥둥 효과
  useEffect(() => {
    let animationFrameId: number
    const start = Date.now()

    const animate = () => {
      const now = Date.now()
      const elapsed = now - start
      setFloatY(Math.sin(elapsed / 600) * 6) // 진폭을 줄여서 더 얌전하게
      animationFrameId = requestAnimationFrame(animate)
    }

    animate()
    return () => cancelAnimationFrame(animationFrameId)
  }, [])

  // 눈 깜빡임 효과
  useEffect(() => {
    let timeoutId: NodeJS.Timeout

    const blink = () => {
      setIsBlinking(true)
      setTimeout(() => setIsBlinking(false), 150)
      
      const nextBlink = Math.random() * 4000 + 2000
      timeoutId = setTimeout(blink, nextBlink)
    }
    
    timeoutId = setTimeout(blink, 2000)
    return () => clearTimeout(timeoutId)
  }, [])

  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8 pb-32">
      {/* 극도로 단순하고 직관적인 캐릭터 'Hopi' */}
      <div 
        className="mb-6 flex flex-col items-center justify-center"
        style={{ transform: `translateY(${floatY}px)` }}
      >
        {/* 디테일을 다 빼고, 얼굴 형태와 눈 2개만 남긴 미니멀 로봇 */}
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#161b22] border border-gray-700/50 shadow-sm">
          <div className="flex space-x-3">
            <div className={`w-2.5 bg-blue-400 rounded-full transition-all duration-150 ${isBlinking ? 'h-0.5' : 'h-2.5'}`}></div>
            <div className={`w-2.5 bg-blue-400 rounded-full transition-all duration-150 ${isBlinking ? 'h-0.5' : 'h-2.5'}`}></div>
          </div>
        </div>
      </div>
      
      {/* 환영 메시지 */}
      <div className="text-center">
        <h1 className="text-lg font-medium text-gray-300">
          안녕하세요! 저는 Hopilot입니다.
        </h1>
      </div>
    </div>
  )
}
