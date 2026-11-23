import {
  createMessageConnection,
  MessageConnection,
  AbstractMessageReader,
  AbstractMessageWriter,
  Message,
  DataCallback,
  NotificationType,
  Disposable,
  CancellationToken
} from 'vscode-jsonrpc/browser'
import { RequestBus } from './RequestBus'

// ─────────────────────────────────────────────
// Transport Layer (IPC 브릿지)
// ─────────────────────────────────────────────

class IpcMessageReader extends AbstractMessageReader {
  public listen(callback: DataCallback): Disposable {
    const cleanup = window.api.on('ho-server-signal', (payload) => {
      callback(payload as Message)
    })
    return { dispose: cleanup }
  }
}

class IpcMessageWriter extends AbstractMessageWriter {
  public write(msg: Message): Promise<void> {
    window.api.send('ho-signal', msg)
    return Promise.resolve()
  }
  public end(): void {}
}

// ─────────────────────────────────────────────
// SignalBus — Python signal_bus.py 대응
// ─────────────────────────────────────────────

export class SignalBus {
  private connection: MessageConnection
  public readonly requests: RequestBus

  constructor() {
    const reader = new IpcMessageReader()
    const writer = new IpcMessageWriter()
    this.connection = createMessageConnection(reader, writer)
    this.connection.listen()
    this.requests = new RequestBus(this.connection)
  }

  /**
   * [EventBus] 단방향 이벤트 발신. 응답을 기다리지 않음.
   * Python: signal_bus.emit(signal)
   */
  public async emit<P>(method: string, params: P): Promise<void> {
    const type = new NotificationType<P>(method)
    await this.connection.sendNotification(type, params as any)
  }

  /**
   * [RequestBus] 프론트 → 백엔드 요청 후 단일 응답 대기.
   * Python: signal_bus.invoke_background(signal, callback)
   */
  public async invoke<P, R>(method: string, params: P, token?: CancellationToken): Promise<R> {
    return this.requests.invoke<P, R>(method, params, token)
  }

  /**
   * [StreamBus] 요청 후 청크($/progress)를 onChunk로 수신하고, 완료 시 최종 응답 반환.
   * Python: signal_bus.stream_background(signal, callback)
   */
  public async stream<P, C, R>(
    method: string,
    params: P,
    onChunk: (chunk: C, token?: string | number) => void,
    token?: CancellationToken,
  ): Promise<R> {
    const progressType = new NotificationType<{ token: string | number; chunk: C }>('$/progress')

    const disposable = this.connection.onNotification(progressType, ({ token, chunk }) => {
      onChunk(chunk, token)
    })

    try {
      return await this.invoke<P, R>(method, params, token)
    } finally {
      disposable.dispose()
    }
  }

  public dispose(): void {
    this.connection.dispose()
  }
}

export const signalBus = new SignalBus()
