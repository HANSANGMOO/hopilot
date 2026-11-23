from dataclasses import dataclass, field
from typing import Dict, Optional, Type, TypeVar

T = TypeVar("T")


@dataclass
class ToolDependency:
    """ToolService 빌트인 툴 생성에 필요한 의존성 컨테이너."""
    _container: Dict[Type, object] = field(default_factory=dict)

    def register(self, type_: Type[T], instance: T) -> None:
        self._container[type_] = instance

    def get(self, type_: Type[T]) -> Optional[T]:
        return self._container.get(type_)  # type: ignore[return-value]
