import { useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import ChatWindow from './components/chat/ChatWindow'
import ChatInput from './components/chat/ChatInput'
import WelcomeScreen from './components/chat/WelcomeScreen'
import { Message } from './types/chat'

function App() {
  // 메시지를 빈 배열로 초기화합니다.
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')

  // 텍스트를 받아서 전송하는 로직 (버튼 클릭이나 엔터, 또는 추천 검색어 클릭 시)
  const handleSend = (text?: string) => {
    const textToSend = text || input
    if (!textToSend.trim()) return

    const newUserMsg: Message = { id: Date.now(), role: 'user', content: textToSend }
    setMessages((prev) => [...prev, newUserMsg])

    // 직접 입력한 경우에만 인풋창을 비웁니다.
    if (!text) setInput('')

    setTimeout(() => {
      const mockAiMsg: Message = {
        id: Date.now() + 1,
        role: 'ai',
        content: `입력하신 **"${textToSend}"** 에 대한 답변입니다!\n\n\`\`\`javascript\nconsole.log("Welcome Screen 적용 완료!");\n\`\`\``
      }
      setMessages((prev) => [...prev, mockAiMsg])
    }, 1000)
  }

  return (
    <div className="flex h-screen w-full bg-[#0d1117] font-sans text-gray-200">
      <Sidebar />
      <main className="relative flex flex-1 flex-col overflow-hidden bg-[#0d1117]">
        {/* 대화 기록이 없으면 초기 화면을, 있으면 채팅창을 렌더링합니다. */}
        {messages.length === 0 ? <WelcomeScreen /> : <ChatWindow messages={messages} />}

        <ChatInput input={input} setInput={setInput} onSend={() => handleSend()} />
      </main>
    </div>
  )
}

export default App
