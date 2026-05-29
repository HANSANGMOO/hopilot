import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  role: 'user' | 'ai'
  content: string
  timestamp: string
}

function App(): JSX.Element {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-1',
      role: 'ai',
      content: 'Hello! I am Hopilot, your advanced agentic AI coding assistant. How can I help you today?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return

    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setMessages((prev) => [...prev, newMessage])
    setInput('')

    // Mock AI Response
    setTimeout(() => {
      const aiResponse: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'ai',
        content: "That's an interesting point! Since we haven't connected the backend yet, I'm just echoing a placeholder response. Let's wire up the WebSocket next!",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages((prev) => [...prev, aiResponse])
    }, 800)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-container">
      {/* Header */}
      <header className="chat-header">
        <h1>Hopilot</h1>
        <div className="status-indicator">
          <div className="pulse"></div>
          <span>Ready (Local)</span>
        </div>
      </header>

      {/* Messages Area */}
      <main className="messages-area">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.role}`}>
            <span className="message-time">
              {msg.role === 'user' ? 'You' : 'Hopilot'} • {msg.timestamp}
            </span>
            <div className="message-bubble">
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="input-area">
        <div className="input-wrapper">
          <input
            type="text"
            className="chat-input"
            placeholder="Send a message to Hopilot..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button 
            className="send-button" 
            onClick={handleSend}
            disabled={!input.trim()}
          >
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </footer>
    </div>
  )
}

export default App
