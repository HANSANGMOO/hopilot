import { defineSignal } from './signal'

/**
 * 사용자가 프론트엔드에서 입력한 요구사항(Prompt)을 백엔드 에이전트로 전송하는 시그널입니다.
 */
export const SendUserRequestSignal = defineSignal<{ session_id: string; query: string }>('SendUserRequestSignal')

/**
 * 백엔드 Copilot 에이전트가 생성한 출력(청크)을 프론트엔드로 전송하는 시그널입니다.
 */
export const CopilotChunkSignal = defineSignal<{ chunk: string; is_done?: boolean }>('CopilotChunkSignal')
