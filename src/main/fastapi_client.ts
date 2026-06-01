import { ipcMain, WebContents } from 'electron'
import WebSocket from 'ws' // Node.js 환경의 웹소켓 라이브러리
import { Channel } from './core/channel'

/**
 * 오직 웹소켓 연결(물리적 네트워크)과 생명주기(Lifecycle)만을 관리합니다.
 * 파이썬 백엔드의 `python/server/fastapi_server.py`와 완벽하게 대칭을 이룹니다.
 */
export class FastAPIClient {
  private ws: WebSocket | null = null
  private readonly url = 'ws://127.0.0.1:8000/ws/hopilot'
  private reconnectTimer: NodeJS.Timeout | null = null
  private webContents: WebContents | null = null

  // 비즈니스 로직(파싱)을 담당할 추상화된 채널 객체
  private channel: Channel | null = null

  constructor() {
    // 1. [React -> Main -> Python]
    // React(Preload)에서 쏜 HOSignal을 Main이 받으면, Channel을 통해 파이썬으로 전송합니다.
    ipcMain.on('ho-signal', (_event, signal) => {
      if (this.channel) {
        this.channel.send(signal)
      } else {
        console.warn(
          '[FastAPIClient] 웹소켓 채널이 아직 연결되지 않아 시그널을 버립니다:',
          signal?.type
        )
      }
    })
  }

  /**
   * 파이썬의 결과를 React 화면으로 쏴주기 위해 렌더러 창(WebContents)을 등록합니다.
   */
  public attachWebContents(webContents: WebContents) {
    this.webContents = webContents
  }

  /**
   * 파이썬 서버와 웹소켓 연결을 시작합니다.
   */
  public connect() {
    if (this.ws) return

    console.log(`[FastAPIClient] ${this.url} 연결 시도 중...`)
    this.ws = new WebSocket(this.url)

    this.ws.on('open', () => {
      console.log('[FastAPIClient] 파이썬 서버와 웹소켓 연결 완료!')
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }

      // ★ 핵심: 연결이 성공하면 Channel 객체를 생성하여 네트워크 기능(콜백)을 주입합니다. ★
      this.channel = new Channel(
        // 주입 1: 밖으로 문자를 던지는 송신 함수
        (text: string) => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(text)
          }
        },
        // 주입 2: 수신 이벤트 리스너를 등록해주는 함수 (파이썬의 listen 루프를 대체)
        (callback) => {
          this.ws!.on('message', (data) => {
            callback(data.toString())
          })
        },
        // 주입 3: 파싱(JSON -> 객체)이 모두 끝난 예쁜 데이터를 전달받을 목적지 함수
        (payload: any) => {
          console.log('[FastAPIClient] 파이썬에서 시그널 수신:', payload?.type)
          if (this.webContents) {
            // 다시 React 화면으로 토스!
            this.webContents.send('ho-server-signal', payload)
          }
        }
      )
    })

    this.ws.on('close', () => {
      console.warn('[FastAPIClient] 파이썬 연결 끊어짐. 3초 후 재연결 시도...')
      this.ws = null
      this.channel = null // 연결이 끊어지면 채널도 파괴합니다.
      this.scheduleReconnect()
    })

    this.ws.on('error', (err) => {
      console.error('[FastAPIClient] 웹소켓 에러:', err.message)
      this.ws?.close()
    })
  }

  private scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => this.connect(), 3000)
    }
  }
}
