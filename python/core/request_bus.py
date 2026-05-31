from typing import Callable, Dict, Type, TypeVar, Awaitable

class BaseRequest:
    """모든 요청(Request) 객체의 최상위 부모 클래스"""
    pass

Q = TypeVar('Q', bound=BaseRequest)
R = TypeVar('R')

class RequestBus:
    def __init__(self) -> None:
        self._handlers: Dict[Type[BaseRequest], Callable[[Q], Awaitable[R]]] = {}

    def register(self, request_type: Type[Q], handler: Callable[[Q], Awaitable[R]]) -> None:
        """특정 요청 타입에 대한 비동기 처리기(Handler)를 명시적으로 등록합니다."""
        if request_type in self._handlers:
            raise ValueError(f"'{request_type.__name__}'에 대한 핸들러가 이미 존재합니다.")
            
        self._handlers[request_type] = handler

    async def send(self, request: Q) -> R:
        """
        요청 객체를 받아 해당 핸들러에게 위임하고, 처리 결과(Response)를 비동기적으로 대기하여 반환합니다.
        
        * 주의: 백그라운드 스레드(Tool Engine)에서 이 함수를 통해 메인 루프에 요청을 보낼 때는 
          직접 await를 쓸 수 없으므로 `asyncio.run_coroutine_threadsafe`를 사용해야 합니다.
        """
        request_type = type(request)
        
        if request_type not in self._handlers:
            raise ValueError(f"'{request_type.__name__}'을(를) 처리할 핸들러가 등록되지 않았습니다.")
            
        handler = self._handlers[request_type]
        
        # 비동기 핸들러를 실행하고, 그 결괏값을 호출자에게 반환합니다.
        return await handler(request)

    def handle(self, request_type: Type[Q]) -> Callable[[Callable[[Q], Awaitable[R]]], Callable[[Q], Awaitable[R]]]:
        """
        데코레이터를 사용하여 핸들러 함수를 등록합니다.
        
        [사용 예시]
        @request_bus.handle(ToolApproveRequest)
        async def handle_tool_execution(request: ToolApproveRequest) -> bool:
            return await approve_tool(request.tool_name)
        """
        def decorator(handler: Callable[[Q], Awaitable[R]]) -> Callable[[Q], Awaitable[R]]:
            self.register(request_type, handler)
            return handler
        return decorator
