import { ipcMain, dialog, shell, BrowserWindow } from 'electron'
import { fileURLToPath } from 'url'
import { getAttachmentPreview } from './handler'

export function registerAttachmentHandlers(getWindow: () => BrowserWindow | null): void {
  ipcMain.handle('show-open-dialog', async () => {
    const win = getWindow()
    if (!win) return []
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'] },
        { name: 'Files',  extensions: ['pdf', 'txt', 'md', 'py', 'js', 'ts', 'tsx', 'jsx', 'json', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'] },
        { name: 'All Files', extensions: ['*'] },
      ],
    })
    if (canceled) return []
    return Promise.all(filePaths.map(getAttachmentPreview))
  })

  ipcMain.handle('show-folder-dialog', async () => {
    const win = getWindow()
    if (!win) return null
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
      properties: ['openDirectory'],
    })
    return canceled ? null : filePaths[0]
  })

  ipcMain.handle('open-path', (_event, fileUrl: string) => {
    const filePath = fileUrl.startsWith('file://') ? fileURLToPath(fileUrl) : fileUrl
    return shell.openPath(filePath)
  })
}
