export {}

declare global {
  interface Window {
    api: {
      /** Renderer → Main 단방향 발신 */
      send: (channel: string, data?: unknown) => void
      /** Main → Renderer 수신 등록. 반환값 호출 시 리스너 해제 */
      on: (channel: string, callback: (data: unknown) => void) => () => void
      /** Renderer → Main 요청-응답 (양방향) */
      invoke: (channel: string, data?: unknown) => Promise<unknown>
      /** 드래그앤드롭 File 객체로부터 절대 경로 반환 */
      getPathForFile: (file: File) => string
    }
  }
}
