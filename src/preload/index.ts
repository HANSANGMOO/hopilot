import { contextBridge, ipcRenderer, IpcRendererEvent, webUtils } from 'electron'

const api = {
  /** Renderer → Main (단방향 발신) */
  send: (channel: string, data?: unknown): void => {
    ipcRenderer.send(channel, data)
  },

  /** Main → Renderer (수신 등록). 반환값 호출 시 리스너 해제 */
  on: (channel: string, callback: (data: unknown) => void): (() => void) => {
    const listener = (_event: IpcRendererEvent, data: unknown) => callback(data)
    ipcRenderer.on(channel, listener)
    return () => ipcRenderer.removeListener(channel, listener)
  },

  /** Renderer → Main 요청-응답 (양방향) */
  invoke: (channel: string, data?: unknown): Promise<unknown> => {
    return ipcRenderer.invoke(channel, data)
  },

  /** 드래그앤드롭 File 객체로부터 절대 경로 반환 */
  getPathForFile: (file: File): string => webUtils.getPathForFile(file),
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.api = api
}
