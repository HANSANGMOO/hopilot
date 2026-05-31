# Hopilot EventBus & RequestBus Implementation Guide

본 문서는 Hopilot 로컬 애플리케이션의 핵심 코어 통신 계층인 `EventBus`와 `RequestBus`의 아키텍처 설계 배경과 구현 방식을 요약합니다.

## 1. 아키텍처 철학 (Architecture Philosophy)
Hopilot은 단일 유저 기반의 로컬 애플리케이션입니다. 따라서 복잡한 백그라운드 워커(Worker) 프로세스나 거대한 큐(Queue) 시스템 대신, 파이썬 네이티브 비동기 생태계(`asyncio`)와 정적 타입 시스템(`TypeVar`, `Type`)을 활용하여 **가장 가볍고, 견고하며, 우아한(Pythonic) 코드**를 작성하는 것에 집중했습니다.

모든 버스(Bus) 시스템은 문자열 기반의 토픽(Topic) 매칭을 버리고, **클래스(Class Type) 자체를 구독/발행의 식별자로 사용**합니다. 이를 통해 완벽한 타입 안정성(Type Safety)을 확보했습니다.

---

## 2. EventBus (이벤트 버스)
- **위치**: `python/core/event_bus.py`
- **패턴**: 발행-구독 (Pub-Sub) 패턴 (1 : N 매칭)
- **목적**: 시스템 내에서 발생한 상태 변화(예: LLM 청크 생성)를 여러 구독자(웹소켓, 파일 로거 등)에게 '통보'할 때 사용합니다. 결괏값을 반환하지 않습니다.

### 핵심 설계
* **Fire-and-Forget (비동기 위임)**: 
  퍼블리셔(LLM 계층)가 `publish()`를 호출하면, 콜백 함수들은 `asyncio.create_task()`를 통해 백그라운드 이벤트 루프에 던져집니다. 퍼블리셔는 웹소켓 전송 속도 등에 의해 1밀리초도 블로킹되지 않고 즉시 다음 작업을 수행합니다. (Backpressure 원천 차단)
* **메모리 누수 및 예외 처리 (GC 안전장치)**: 
  던져진 태스크가 파이썬 가비지 컬렉터(GC)에 의해 무음으로 증발하는 것을 막기 위해 `_background_tasks` Set에 저장하여 생명 주기를 관리합니다. 
  또한 `add_done_callback`을 통해 커스텀 핸들러(`_task_done_handler`)를 부착하여, 태스크 실행 중 에러가 발생해도 메인 앱이 죽지 않고 로거(`logger.error`)에 안전하게 기록되도록 설계했습니다.
* **우아한 데코레이터**: `@bus.on(EventClass)` 형태로 간편하게 구독을 등록할 수 있습니다.

---

## 3. RequestBus (리퀘스트 버스)
- **위치**: `python/core/request_bus.py`
- **패턴**: 미디에이터 (Mediator / Request-Reply) 패턴 (1 : 1 매칭)
- **목적**: 특정 작업을 위임하고 그 결과를 호출자에게 반드시 돌려받아야 할 때 사용합니다. (예: Tool Engine에게 특정 도구 실행 요청)

### 핵심 설계
* **단일 핸들러 제약**: 
  EventBus와 달리, 특정 `Request` 클래스에 대한 처리기(Handler)는 오직 1개만 등록할 수 있습니다. 중복 등록 시 에러를 발생시켜 책임의 분산을 막습니다.
* **표준 네이밍 및 코루틴 기반 지연 실행 (Future 대행)**: 
  메서드명을 글로벌 표준인 `send`로 통일했습니다. 무거운 `asyncio.Future` 객체를 억지로 만들지 않으며, `send()` 메서드 자체가 `async def`로 구현되어 있어 핸들러의 코루틴 결과값을 자연스럽게 비동기 반환(`await handler(request)`)합니다.
* **스레딩(Threading) 호환성 고려**: 
  향후 Tool Engine의 백그라운드 스레드에서 메인 루프의 RequestBus로 `send()`를 호출할 때는 직접 `await`를 사용할 수 없으므로, 메인 스레드와의 통신을 위해 `asyncio.run_coroutine_threadsafe(bus.send(), main_loop).result()`를 사용하여 스레드 안전(Thread-safe)하게 브릿징하도록 아키텍처 방향을 확정했습니다.
* **우아한 데코레이터**: `@request_bus.handle(RequestClass)` 형태로 간편하게 미디에이터를 등록할 수 있습니다.
