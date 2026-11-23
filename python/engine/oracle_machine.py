from core.oracle import OracleState
from core.copilot import Tape

class OracleMachine:
    """
    Oracle 아키텍처의 핵심 실행 엔진.
    Tape, Head, State, Transition function을 사용하여 
    결정론적인 루프를 수행한다.
    """
    def __init__(self):
        # 머신의 초기 상태를 설정합니다.
        self.state: OracleState = OracleState.INIT

    async def run(self, tape: Tape) -> AsyncGenerator[Any, None]:
        """
        Oracle 아키텍처의 메인 루프를 실행합니다.
        """
        pass
