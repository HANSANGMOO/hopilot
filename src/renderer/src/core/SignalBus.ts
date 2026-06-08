import {
  createMessageConnection,
  MessageConnection,
  AbstractMessageReader,
  AbstractMessageWriter,
  Message,
  DataCallback,
  RequestType,
  NotificationType,
  Disposable,
  CancellationToken
} from 'vscode-jsonrpc/browser'

// 1. IpcMessageReader: Forwards messages ('ho-server-signal') from the Main process to vscode-jsonrpc
class IpcMessageReader extends AbstractMessageReader {
  private disposable: (() => void) | null = null

  public listen(callback: DataCallback): Disposable {
    const listener = (_event: any, payload: any) => {
      // payload is already JSON.parsed as an Object (Message) in the Main process (Channel)
      callback(payload as Message)
    }

    // @ts-ignore: using window.electron.ipcRenderer
    window.electron.ipcRenderer.on('ho-server-signal', listener)

    this.disposable = () => {
      // @ts-ignore
      window.electron.ipcRenderer.removeListener('ho-server-signal', listener)
    }

    return {
      dispose: () => {
        if (this.disposable) {
          this.disposable()
          this.disposable = null
        }
      }
    }
  }
}

// 2. IpcMessageWriter: Sends messages created by vscode-jsonrpc to the Main process ('ho-signal')
class IpcMessageWriter extends AbstractMessageWriter {
  public write(msg: Message): Promise<void> {
    // @ts-ignore: using window.api.sendSignal
    window.api.sendSignal(msg)
    return Promise.resolve()
  }

  public end(): void {}
}

// 3. SignalBus Class Definition
export class SignalBus {
  private connection: MessageConnection

  constructor() {
    const reader = new IpcMessageReader()
    const writer = new IpcMessageWriter()
    
    // Create vscode-jsonrpc connection
    this.connection = createMessageConnection(reader, writer)
    
    // Start connection listening loop
    this.connection.listen()
    console.log('[SignalBus] vscode-jsonrpc connection initialized successfully')
  }

  /**
   * Sends a Request to the backend and waits for the final response.
   * @param method JSON-RPC method name (e.g., 'copilot/send')
   * @param params Parameters to send (e.g., { session_id: '...', query: '...' })
   * @param token (Optional) CancellationToken for cancellation
   */
  public async sendRequest<P, R>(
    method: string, 
    params: P, 
    token?: CancellationToken
  ): Promise<R> {
    const requestType = new RequestType<P, R, any>(method)
    return this.connection.sendRequest(requestType, params, token)
  }

  /**
   * Receives real-time '$/progress' streaming notifications sent from the backend.
   * @param callback Callback in the form of (token: Request ID, chunk: Actual data)
   */
  public onProgress<T>(callback: (params: { token: string | number, chunk: T }) => void): Disposable {
    const notificationType = new NotificationType<{ token: string | number, chunk: T }>('$/progress')
    return this.connection.onNotification(notificationType, callback)
  }

  /**
   * Sends a one-way Notification to the backend.
   */
  public sendNotification<P>(method: string, params: P): void {
    const notificationType = new NotificationType<P>(method)
    this.connection.sendNotification(notificationType, params)
  }

  /**
   * Closes the connection.
   */
  public dispose() {
    this.connection.dispose()
  }
}

// Export Singleton Instance
export const signalBus = new SignalBus()
