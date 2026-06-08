/**
 * Specifications for user request transmission parameters
 */
export interface SendUserRequestParams {
  session_id: string
  query: string
}

/**
 * Specifications for streaming chunk data received from the backend
 */
export interface CopilotChunkDTO {
  chunk: any // Maps to Python's HOChunk data
  msg_id: string
  session_id: string
  role: string
}
