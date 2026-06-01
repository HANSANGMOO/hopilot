# Hopilot EventBus Architecture Design (Handover)

## 1. 배경 및 목적 (Background)

- 현재 `Hopilot` 백엔드는 `FastAPI` 기반으로 동작하며, 웹소켓(WebSocket)을 통해 프론트엔드(Electron/React)와 통신합니다.
- 현재 `AppController`의 웹소켓 엔드포인트는 수신된 메시지를 `CopilotHandler`로 넘겨 처리한 뒤 즉시 단일 응답을 반환하는 구조(동기식 에코 형태)로 임시 작성되어 있습니다.
- **해결 과제**: LLM(`CopilotService`)이 생성해 내는 실시간 청크(Chunk)들을 프론트엔드로 끊김없이 스트리밍하기 위해, **사용자 입력을 받는 루프(Receive)**와 **청크를 보내는 루프(Send)**를 비동기적으로 완벽히 분리해야 합니다. 이를 위해 **EventBus** 코어 계층의 도입이 필요합니다.

## 2. EventBus 설계의 두 가지 접근법 비교

다음 LLM 세션에서는 아래의 두 가지 방식 중 사용자가 선택하는 방향으로 `core/bus.py`를 구현해야 합니다.

### 방식 A: Queue 기반 EventBus (LLM 스트리밍 표준 / 추천 방식)

`asyncio.Queue`를 활용하여 퍼블리셔(LLM)와 구독자(WebSocket) 간에 버퍼를 두는 방식.

- **동작 원리**:
  1. `AppController`는 `subscribe("chat_stream")`을 호출하여 전용 큐(`asyncio.Queue`)를 발급받습니다.
  2. 큐에서 데이터를 꺼내 프론트엔드로 전송(`websocket.send_json`)하는 별도의 비동기 태스크(`asyncio.create_task`)를 백그라운드에서 무한히 돌립니다. (`while True: await queue.get()`)
  3. `CopilotService`는 큐의 상태나 웹소켓을 전혀 모르며, 오직 `publish("chat_stream", chunk)`만 호출하여 데이터를 밀어 넣습니다.
- **장점**:
  - 네트워크 지연으로 인해 프론트엔드로 데이터 전송이 느려지더라도(Backpressure), LLM 워커의 청크 생성 루프가 블로킹(Blocking)되지 않습니다. 완벽한 디커플링.
- **단점**: 별도의 백그라운드 태스크를 생성하고 관리해야 하므로 구조가 다소 낯설 수 있습니다.

### 방식 B: Callback 기반 EventBus (전통적인 PyQt Signal/Slot 스타일)

함수 포인터를 리스트에 저장해 두었다가 이벤트 발생 시 호출하는 방식.

- **동작 원리**:
  1. `AppController`는 송신 역할을 하는 비동기 콜백 함수(`async def on_chunk(data): await websocket.send_json(data)`)를 정의합니다.
  2. `subscribe("chat_stream", on_chunk)`를 통해 함수 자체를 EventBus에 등록합니다.
  3. `CopilotService`가 `publish`를 호출하면, EventBus가 등록된 모든 콜백 함수를 순회하며 `await callback(chunk)`를 실행합니다.
- **장점**:
  - PyQt의 Signal-Slot 패턴과 100% 동일한 개념이므로 매우 직관적이고 코드가 짧습니다.
- **단점**:
  - 웹소켓 송신(네트워크 I/O) 처리에 시간이 걸리면, `await callback`에서 병목이 발생해 **퍼블리셔(LLM 생성 로직) 전체가 블로킹**될 위험이 있습니다.

## 3. 다음 세션(Next Session) 진행 가이드

이 문서를 읽은 AI 어시스턴트는 사용자에게 두 가지 방식(Queue vs Callback) 중 어느 쪽으로 구현을 진행할지 확인하거나, 사용자가 이미 결정한 방식에 따라 아래 작업을 수행해야 합니다.

1. **`python/core/bus.py` 파일 생성**: 선택된 방식에 맞는 `EventBus` 클래스 구현
2. **`python/main.py` 수정**: `EventBus` 인스턴스를 생성하고, `AppController` 및 `CopilotService`에 의존성 주입(DI)
3. **`python/controller/app_controller.py` 리팩토링**: 기존의 단일 응답(Echo) 로직을 제거하고, EventBus를 수신(Subscribe)하여 송신 루프와 수신 루프를 비동기적으로 분리하는 작업 수행
