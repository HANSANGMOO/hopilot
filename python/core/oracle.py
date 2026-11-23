from enum import Enum

class OracleState(str, Enum):
    """
    Oracle 아키텍처에서 사용하는 머신의 상태.
    ReAct의 EType과 별개로 관리되어 논리적 격리를 유지함.
    """
    INIT = "init"
    EXEC = "exec"
    ORAC = "orac"
    HALT = "halt"
