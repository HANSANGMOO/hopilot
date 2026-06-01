export interface Message {
  id: number
  role: 'user' | 'system' | 'ai'
  content: string
}
