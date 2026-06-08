import { useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import ChatWindow from './components/chat/ChatWindow'
import ChatInput from './components/chat/input'
import WelcomeScreen from './components/chat/WelcomeScreen'
import { Message } from './types/chat'
import { signalBus } from './core/SignalBus'
import { CopilotChunkDTO } from '../../contracts/copilot'

function App() {
  // 메시지를 빈 배열로 초기화합니다.
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')

  // 텍스트를 받아서 전송하는 로직 (버튼 클릭이나 엔터, 또는 추천 검색어 클릭 시)
  const handleSend = async (text?: string) => {
    const textToSend = text || input
    if (!textToSend.trim()) return

    const newUserMsg: Message = { id: Date.now(), role: 'user', content: textToSend }
    setMessages((prev) => [...prev, newUserMsg])

    // 직접 입력한 경우에만 인풋창을 비웁니다.
    if (!text) setInput('')

    const aiMsgId = Date.now() + 1
    const newAiMsg: Message = { id: aiMsgId, role: 'ai', content: '' }
    setMessages((prev) => [...prev, newAiMsg])

    try {
      // 1. 스트리밍(청크) 수신 콜백 등록 (글자가 한 글자씩 렌더링되게 함)
      const progressDisposable = signalBus.onProgress<CopilotChunkDTO>((params) => {
        const chunkDTO = params.chunk
        // 파이썬 백엔드에서 내려주는 청크 텍스트를 누적
        if (chunkDTO.chunk?.text) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === aiMsgId
                ? { ...msg, content: msg.content + chunkDTO.chunk.text }
                : msg
            )
          )
        }
      })

      // 2. 파이썬 백엔드에 JSON-RPC 요청 전송
      console.log('[App] 백엔드로 copilot/send 요청 전송:', textToSend)
      const result = await signalBus.sendRequest('copilot/send', {
        session_id: 'test-session-123',
        query: textToSend
      })
      console.log('[App] 백엔드 최종 응답 수신 완료:', result)

      // 3. 요청이 끝나면 스트리밍 리스너 해제
      progressDisposable.dispose()
    } catch (error) {
      console.error('[App] 요청 중 에러 발생:', error)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMsgId
            ? { ...msg, content: msg.content + '\n\n**[오류가 발생했습니다. 파이썬 서버 연결을 확인하세요.]**' }
            : msg
        )
      )
    }
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
