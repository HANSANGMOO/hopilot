import { nativeImage } from 'electron'
import { readFile } from 'fs/promises'
import { basename, extname } from 'path'

const EXT_TO_MIME: Record<string, string> = {
  jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png',
  gif: 'image/gif',  webp: 'image/webp', bmp: 'image/bmp',
  pdf:  'application/pdf',    txt: 'text/plain',       md:   'text/markdown',
  py:   'text/x-python',     js:  'text/javascript',  ts:   'text/typescript',
  tsx:  'text/typescript',   jsx: 'text/javascript',  json: 'application/json',
  doc:  'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xls:  'application/vnd.ms-excel',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  ppt:  'application/vnd.ms-powerpoint',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}

export interface AttachmentPreview {
  path: string
  name: string
  mimeType: string
  previewUrl: string
}

export interface AttachmentData {
  name: string
  mimeType: string
  data: string // base64, 전송 시점에 사용
}

export async function getAttachmentPreview(filePath: string): Promise<AttachmentPreview> {
  const name     = basename(filePath)
  const ext      = extname(filePath).toLowerCase().slice(1)
  const mimeType = EXT_TO_MIME[ext] ?? 'application/octet-stream'

  const previewUrl = mimeType.startsWith('image/')
    ? nativeImage.createFromPath(filePath).resize({ width: 64, height: 64, quality: 'better' }).toDataURL()
    : ''

  return { path: filePath, name, mimeType, previewUrl }
}

export async function readAttachment(filePath: string): Promise<AttachmentData> {
  const buffer   = await readFile(filePath)
  const name     = basename(filePath)
  const ext      = extname(filePath).toLowerCase().slice(1)
  const mimeType = EXT_TO_MIME[ext] ?? 'application/octet-stream'
  return { name, mimeType, data: buffer.toString('base64') }
}
