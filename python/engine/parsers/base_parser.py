from abc import ABC, abstractmethod
from typing import Iterator


class BaseParser(ABC):
    """
    모든 파일 파서 클래스가 상속받아야 하는 추상 기본 클래스입니다.
    이 클래스는 모든 파서가 'parse' 메소드를 구현하도록 강제합니다.
    """

    @abstractmethod
    def parse(self, path: str) -> str:
        """
        주어진 파일 경로(path)에서 텍스트를 추출하여 문자열로 반환합니다.
        이 메소드는 하위 클래스에서 반드시 재정의(override)되어야 합니다.
        """
        pass

    def parse_pages(self, path: str) -> Iterator[str]:
        """청크 단위로 텍스트를 yield합니다. 기본 구현은 전체를 한 번에 반환합니다."""
        yield self.parse(path)