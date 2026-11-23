import { CancellationToken, Disposable, MessageConnection, RequestType } from 'vscode-jsonrpc/browser'

// ─────────────────────────────────────────────
// RequestBus — Python core/bus/request_bus.py 대응
// 1:1 양방향 요청(invoke)과 역방향 핸들러(handle)를 처리합니다.
// ─────────────────────────────────────────────

export class RequestBus {
  constructor(private connection: MessageConnection) {}

  /**
   * 프론트 → 백엔드 요청 후 단일 응답 대기.
   * Python: signal_bus.invoke_background(signal, callback)
   */
  public async invoke<P, R>(method: string, params: P, token?: CancellationToken): Promise<R> {
    const type = new RequestType<P, R, never>(method)
    return this.connection.sendRequest(type, params as any, token)
  }

  /**
   * 백엔드 → 프론트 역방향 요청 핸들러 등록.
   * Python: signal_bus.push_invoke(method, params) 에 대응.
   */
  public handle<P, R>(
    method: string,
    handler: (params: P, token: CancellationToken) => R | Promise<R>
  ): Disposable {
    return this.connection.onRequest(method, handler as any)
  }
}
