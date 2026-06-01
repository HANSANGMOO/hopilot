# Hopilot WebSocket Communication Design

## 1. 개요 (Overview)

본 문서는 Hopilot 애플리케이션 내 프론트엔드(Electron/React)와 백엔드(Python FastAPI) 간의 통신 아키텍처 설계를 문서화한 것입니다.

초기에는 React(Renderer)에서 Python 서버로 직접 웹소켓을 연결하는 방식을 고려했으나, 보안 향상 및 표준 Electron 개발 경험(DX) 유지를 위해 **"Electron Main 프로세스와 Python 서버 간의 단일 웹소켓 통신"** 아키텍처로 최종 결정되었습니다.

## 2. 아키텍처 데이터 흐름 (Data Flow)

모든 통신은 프론트엔드(Renderer) -> 메인(Main) -> 백엔드(Python) 순으로 단일화된 파이프라인을 거칩니다.

```text
[명령(Command) 입력 흐름]
Renderer ──ipcRenderer.send──► Main ──웹소켓(JSON) 클라이언트 전송──► Python (AppController 웹소켓 라우터)
                                                               │
                                                        process_request 트리거 (내부 로직)
                                                               │
[이벤트(Event) 스트리밍 출력 흐름]                          EventBus.publish(chunk) (LLM 응답)
                                                               │
Renderer ◄──webContents.send── Main ◄─웹소켓(JSON) 클라이언트 수신─── AppController (웹소켓 송신 큐)
```

## 3. 계층별 역할 및 책임

### 3.1. Renderer (React 프론트엔드)

- **역할**: 순수 UI 렌더링 및 사용자 인터랙션 처리.
- **통신 방식**: 파이썬의 존재나 웹소켓 네트워크 처리를 전혀 모릅니다. 오직 `window.electron.ipcRenderer` 모듈만을 사용하여 Electron Main과 소통합니다.

### 3.2. Electron Main (Node.js)

- **역할**: 외부 통신 관문(API Gateway) 및 앱 생명주기 관리.
- **통신 방식**: 파이썬 서버 구동 시, 파이썬의 웹소켓 주소(`ws://127.0.0.1:8000/ws/copilot`)로 접속하는 전용 웹소켓 클라이언트 객체(`PythonWebChannel`)를 유지합니다.
- **기능**:
  1. Renderer로부터 받은 IPC 이벤트를 JSON 포맷으로 직렬화하여 파이썬 웹소켓으로 전달.
  2. 파이썬 웹소켓에서 수신되는 스트리밍 응답(JSON)을 파싱하여, 즉시 `webContents.send`를 통해 Renderer로 전달.

### 3.3. Python AppController (`python/controller/app_controller.py`)

- **역할**: 파이썬 내부 로직과 외부(Electron Main)를 연결하는 웹소켓 서버 엔드포인트.
- **수신(Receive) 처리**: Main에서 날아오는 JSON 문자열을 파싱하여, 파이썬 내부 인프라인 `RequestBus`로 전달하거나 서비스 로직을 트리거합니다.
- **송신(Send) 처리**: `EventBus`를 통해 수집된 내부 이벤트(예: LLM 청크 스트리밍)를 백그라운드 큐(`asyncio.Queue`)에 담아두었다가, 지연 없이 순차적으로 웹소켓을 통해 Main 프로세스로 내보냅니다. (수신과 송신 루프의 비동기적 완벽 분리)

## 4. 본 아키텍처의 강력한 장점

1. **프론트엔드 샌드박싱 보장**: 렌더러 프로세스가 네트워크 계층(웹소켓)에 직접 접근하지 못하도록 격리되므로(Context Isolation), 보안 표준을 완벽히 준수합니다.
2. **개발자 경험(DX) 극대화**: 프론트엔드 개발자는 통신 로직 고민 없이 기존 Electron 표준 방식(`ipcRenderer`)대로 개발할 수 있습니다.
3. **단일 파이프라인 관리**: 단 하나의 웹소켓 터널에서 양방향 명령과 스트리밍을 모두 처리하므로, 코드의 복잡성이 줄어들고 오류 추적이 용이합니다.

## 5. 향후 구현 단계 (Next Steps)

본 설계를 바탕으로 다음과 같은 순서로 코드를 단계적으로 구현할 예정입니다.

1. Python `AppController`의 수신/송신 비동기 분리(Queue 기반) 리팩토링
2. Electron Main에 `PythonWebChannel` (웹소켓 클라이언트) 구축
3. Renderer에서 표준 IPC를 활용한 테스트 및 연동
