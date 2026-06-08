import { ipcMain, WebContents } from 'electron'
import WebSocket from 'ws' // Node.js WebSocket library
import { Channel } from './core/channel'

/**
 * Manages only the physical WebSocket connection and its lifecycle.
 * Perfectly symmetrical to the python backend's `python/server/fastapi_server.py`.
 */
export class FastAPIClient {
  private ws: WebSocket | null = null
  private readonly url = 'ws://127.0.0.1:8000/ws/hopilot'
  private reconnectTimer: NodeJS.Timeout | null = null
  private webContents: WebContents | null = null

  // Abstracted channel object responsible for parsing logic
  private channel: Channel | null = null

  constructor() {
    // 1. [React -> Main -> Python]
    // When Main receives HOSignal from React(Preload), it forwards it to Python via Channel.
    ipcMain.on('ho-signal', (_event, signal) => {
      if (this.channel) {
        this.channel.send(signal)
      } else {
        console.warn(
          '[FastAPIClient] WebSocket channel is not connected yet. Dropping signal:',
          signal?.type
        )
      }
    })
  }

  /**
   * Registers the renderer window (WebContents) to send Python's responses to the React UI.
   */
  public attachWebContents(webContents: WebContents) {
    this.webContents = webContents
  }

  /**
   * Initiates the WebSocket connection with the Python server.
   */
  public connect() {
    if (this.ws) return

    console.log(`[FastAPIClient] Attempting to connect to ${this.url}...`)
    this.ws = new WebSocket(this.url)

    this.ws.on('open', () => {
      console.log('[FastAPIClient] WebSocket connected to Python server successfully!')
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer)
        this.reconnectTimer = null
      }

      // ★ Core: Upon successful connection, inject network callbacks by creating a Channel object. ★
      this.channel = new Channel(
        // Injection 1: Send function to push text out to the network
        (text: string) => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(text)
          }
        },
        // Injection 2: Function to register the receive event listener (replaces Python's listen loop)
        (callback) => {
          this.ws!.on('message', (data) => {
            callback(data.toString())
          })
        },
        // Injection 3: Destination function to receive fully parsed (JSON -> Object) data
        (payload: any) => {
          console.log('[FastAPIClient] Received signal from Python:', payload?.type)
          if (this.webContents) {
            // Forward it back to the React UI!
            this.webContents.send('ho-server-signal', payload)
          }
        }
      )
    })

    this.ws.on('close', () => {
      console.warn('[FastAPIClient] Python connection closed. Attempting to reconnect in 3 seconds...')
      this.ws = null
      this.channel = null // Destroy channel when connection closes.
      this.scheduleReconnect()
    })

    this.ws.on('error', (err) => {
      console.error('[FastAPIClient] WebSocket error:', err.message)
      this.ws?.close()
    })
  }

  private scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => this.connect(), 3000)
    }
  }
}
