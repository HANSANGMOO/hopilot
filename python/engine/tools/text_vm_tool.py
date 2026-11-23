import asyncio
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from core.models import BaseTool, ToolSchema
from utils import get_logger

logger = get_logger("TextVMTool")

_DEFAULT_MAX_CYCLES = 1000
_HARD_LIMIT_MAX_CYCLES = 10000


class VMInstruction(BaseModel):
    model_config = ConfigDict(extra="allow")

    # 선택적 번호 및 레이블 (어셈블리어의 Label 지원!)
    line: Optional[int] = Field(None, description="명령어 라인 번호 (생략 시 배열 순서대로 0, 1, 2... 자동 부여)")
    label: Optional[str] = Field(None, description="점프 대상이 되는 심볼릭 레이블 이름 (예: 'loop_start', 'on_even', 'done')")
    comment: Optional[str] = Field(None, description="명령어 의도나 설명(주석)")

    # 명령어 종류
    op: Literal["SET", "INC", "EVAL", "CALL_PYTHON", "JUMP", "JUMP_IF", "EMIT", "HALT"] = Field(
        ...,
        description=(
            "명령어 종류:\n"
            "- SET: 변수 할당 (var, val)\n"
            "- INC: 변수 1 또는 step만큼 증가 (var, step)\n"
            "- EVAL: 파이썬 식 평가 후 변수 저장 (expr, out_var)\n"
            "- CALL_PYTHON: 파이썬 스크립트 실행 후 결과 저장 (code, out_var)\n"
            "- JUMP: 무조건 레이블/라인으로 점프 (target)\n"
            "- JUMP_IF: 조건 만족 시 레이블/라인으로 점프 (cond_var, expected, target)\n"
            "- EMIT: 메시지 출력 (text)\n"
            "- HALT: 실행 정상 종료 (reason)"
        )
    )

    # Flat 매개변수 (LLM이 번거로운 args 딕셔너리 없이 최상위에 바로 작성 가능)
    var: Optional[str] = Field(None, description="대상 변수명 (SET, INC)")
    val: Optional[Any] = Field(None, description="할당할 값 (SET)")
    step: Optional[int] = Field(None, description="증가값 (INC, 기본 1)")
    expr: Optional[str] = Field(None, description="평가할 파이썬 식 (EVAL, 예: 'n % 2 == 0')")
    out_var: Optional[str] = Field(None, description="결과를 저장할 변수명 (EVAL, CALL_PYTHON)")
    code: Optional[str] = Field(None, description="실행할 파이썬 코드 (CALL_PYTHON)")
    cond_var: Optional[str] = Field(None, description="조건 검사할 변수명 (JUMP_IF)")
    expected: Optional[Any] = Field(None, description="조건 일치 여부 (JUMP_IF, 기본 True)")
    target: Optional[Union[str, int]] = Field(None, description="점프할 대상 레이블 이름 또는 라인 번호 (JUMP, JUMP_IF)")
    text: Optional[str] = Field(None, description="출력할 텍스트 메시지 (EMIT)")
    reason: Optional[str] = Field(None, description="종료 사유 (HALT)")

    # 하위 호환용 args 딕셔너리
    args: Optional[Dict[str, Any]] = Field(default_factory=dict, description="기존 호환용 인자 딕셔너리 (생략 권장)")

    def get_arg(self, key: str, default: Any = None) -> Any:
        """Flat 필드를 우선 조회하고, 없으면 args 딕셔너리에서 폴백 조회합니다."""
        val = getattr(self, key, None)
        if val is not None:
            return val
        if self.args and key in self.args:
            return self.args[key]
        return default


class TextVMArgs(BaseModel):
    program: List[VMInstruction] = Field(
        ...,
        description="텍스트 가상 머신에서 순차 실행할 명령어 목록(Instruction Tape)"
    )
    initial_memory: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="프로그램 실행 전 메모리에 사전 주입할 변수 딕셔너리"
    )
    max_cycles: Optional[int] = Field(
        default=_DEFAULT_MAX_CYCLES,
        description=f"최대 클럭 사이클 수 (기본 {_DEFAULT_MAX_CYCLES}, 대규모 루프 시 최대 {_HARD_LIMIT_MAX_CYCLES}까지 설정 가능)"
    )


class TextVirtualMachine:
    """레이블 점프와 Flat 매개변수를 지원하는 텍스트 기반 가상 컴퓨터 런타임."""

    def __init__(self, program: List[VMInstruction], memory: Dict[str, Any], max_cycles: int = _DEFAULT_MAX_CYCLES):
        self.memory: Dict[str, Any] = dict(memory)
        self.max_cycles = min(max_cycles, _HARD_LIMIT_MAX_CYCLES)
        self.pc: int = 0
        self.halted: bool = False
        self.halt_reason: str = ""
        self.logs: List[str] = []
        self.emitted: List[str] = []

        # 어셈블러 1차 패스: 라인 번호 자동 채번 및 심볼릭 레이블(Label) 테이블 빌드
        self.instructions: Dict[int, VMInstruction] = {}
        self.label_table: Dict[str, int] = {}

        for idx, raw_instr in enumerate(program):
            assigned_line = raw_instr.line if raw_instr.line is not None else idx
            raw_instr.line = assigned_line
            self.instructions[assigned_line] = raw_instr

            if raw_instr.label:
                cleaned_label = str(raw_instr.label).strip()
                self.label_table[cleaned_label] = assigned_line

    def log(self, text: str):
        self.logs.append(text)

    def resolve_target(self, target: Union[str, int, None]) -> Optional[int]:
        """레이블 이름 또는 라인 번호를 실제 대상 라인 번호(PC)로 변환합니다."""
        if target is None:
            return None
        if isinstance(target, int):
            return target
        if isinstance(target, str):
            target_str = target.strip()
            if target_str in self.label_table:
                return self.label_table[target_str]
            # 문자열 숫자인 경우 ("5")
            if target_str.isdigit():
                return int(target_str)
        return None

    def execute_python_code(self, code: str) -> Any:
        local_scope = {"memory": dict(self.memory), "output": None}
        global_scope = {"__builtins__": __builtins__}
        try:
            exec(code, global_scope, local_scope)
            return local_scope.get("output", local_scope.get("result", "OK"))
        except Exception as e:
            return f"Error: {e}"

    def eval_expression(self, expr: str) -> Any:
        try:
            return eval(expr, {"__builtins__": __builtins__}, dict(self.memory))
        except Exception as e:
            return f"EvalError: {e}"

    def step(self):
        if self.halted:
            return

        if self.pc not in self.instructions:
            self.halted = True
            self.halt_reason = f"PC={self.pc}에 해당하는 명령어가 없어 비정상 종료되었습니다."
            self.log(f"[HALT] {self.halt_reason}")
            return

        instr = self.instructions[self.pc]
        op = instr.op
        label_str = f"[{instr.label}] " if instr.label else ""
        comment_str = f" // {instr.comment}" if instr.comment else ""
        self.log(f"[PC={self.pc:02d}] {label_str}{op}{comment_str}")

        next_pc = self.pc + 1

        try:
            match op:
                case "SET":
                    var = instr.get_arg("var")
                    val = instr.get_arg("val")
                    if var:
                        self.memory[var] = val
                        self.log(f"       └── Memory[{var}] = {repr(val)}")

                case "INC":
                    var = instr.get_arg("var")
                    step = instr.get_arg("step", 1)
                    if var:
                        self.memory[var] = self.memory.get(var, 0) + step
                        self.log(f"       └── Memory[{var}] += {step} (현재: {self.memory[var]})")

                case "EVAL":
                    expr = instr.get_arg("expr", "")
                    out_var = instr.get_arg("out_var")
                    res = self.eval_expression(expr)
                    if out_var:
                        self.memory[out_var] = res
                        self.log(f"       └── EVAL('{expr}') -> Memory[{out_var}] = {repr(res)}")

                case "CALL_PYTHON":
                    code = instr.get_arg("code", "")
                    out_var = instr.get_arg("out_var")
                    res = self.execute_python_code(code)
                    if out_var:
                        self.memory[out_var] = res
                        self.log(f"       └── PYTHON_EXEC -> Memory[{out_var}] = {repr(res)}")

                case "JUMP":
                    raw_target = instr.get_arg("target")
                    target_pc = self.resolve_target(raw_target)
                    if target_pc is not None:
                        self.log(f"       └── [UNCONDITIONAL JUMP] Target '{raw_target}' -> Jump to PC={target_pc:02d}")
                        next_pc = target_pc
                    else:
                        self.log(f"       └── [JUMP ERROR] Target '{raw_target}' not found!")

                case "JUMP_IF":
                    cond_var = instr.get_arg("cond_var")
                    expected = instr.get_arg("expected", True)
                    raw_target = instr.get_arg("target")
                    target_pc = self.resolve_target(raw_target)

                    actual = self.memory.get(cond_var) if cond_var else None

                    # cond_var가 생략되면 무조건 점프로 간주하거나, expected와 actual이 일치하면 점프
                    if cond_var is None or actual == expected:
                        if target_pc is not None:
                            self.log(f"       └── [JUMP CONDITION MET] Memory[{cond_var}] == {expected} -> Jump to '{raw_target}'(PC={target_pc:02d})")
                            next_pc = target_pc
                        else:
                            self.log(f"       └── [JUMP ERROR] Target '{raw_target}' not found!")
                    else:
                        self.log(f"       └── [JUMP CONDITION NOT MET] Memory[{cond_var}]({actual}) != {expected} -> Continue")

                case "EMIT":
                    text = str(instr.get_arg("text", ""))
                    self.emitted.append(text)
                    self.log(f"       └── EMIT: \"{text}\"")

                case "HALT":
                    self.halted = True
                    self.halt_reason = str(instr.get_arg("reason", "정상 종료"))
                    self.log(f"       └── [HALT] 사유: {self.halt_reason}")

        except Exception as e:
            self.halted = True
            self.halt_reason = f"명령어 실행 중 오류 발생: {e}"
            self.log(f"       └── [ERROR HALT] {self.halt_reason}")

        self.pc = next_pc

    def run(self) -> Dict[str, Any]:
        cycles = 0
        while not self.halted and cycles < self.max_cycles:
            self.step()
            cycles += 1

        if cycles >= self.max_cycles and not self.halted:
            self.halted = True
            self.halt_reason = f"최대 클럭 사이클({self.max_cycles})을 초과하여 강제 중단되었습니다 (무한 루프 방지)."
            self.log(f"[TIMEOUT] {self.halt_reason}")

        return {
            "halt_reason": self.halt_reason,
            "cycles_run": cycles,
            "final_memory": self.memory,
            "emitted_messages": self.emitted,
            "execution_trace": "\n".join(self.logs),
        }


class TextVMTool(BaseTool):
    id = "run_text_vm"
    name = "run_text_vm"
    description = (
        "텍스트 가상 머신(Text Virtual Machine / Turing Machine) 실행 도구입니다. "
        "단순한 1회성 응답이 아닌, 조건 분기(If-Else), 반복 루프(Loop & Retry), "
        "상태 보존(Memory), 자기 수정(Self-Correction) 등의 복잡한 절차적 로직을 "
        "단 하나의 텍스트 프로그램(Instruction Tape)으로 컴파일하여 고속으로 일괄 실행할 때 사용합니다. "
        "지원 명령어: 'SET', 'INC', 'EVAL', 'CALL_PYTHON', 'JUMP', 'JUMP_IF', 'EMIT', 'HALT'. "
        "- 라인 번호 대신 'label'과 'target'을 이용한 심볼릭 점프를 적극 권장합니다. "
        "- 번거로운 args 딕셔너리 없이 var, val, expr, out_var, target 등을 최상위 필드로 바로 작성할 수 있습니다."
    )
    input_schema = TextVMArgs

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.input_schema.model_json_schema(),
        )

    async def execute(
        self,
        program: List[Dict[str, Any]] | List[VMInstruction],
        initial_memory: Optional[Dict[str, Any]] = None,
        max_cycles: Optional[int] = _DEFAULT_MAX_CYCLES,
    ) -> str:
        instructions: List[VMInstruction] = []
        for item in program:
            if isinstance(item, VMInstruction):
                instructions.append(item)
            elif isinstance(item, dict):
                instructions.append(VMInstruction(**item))

        mem = initial_memory or {}
        cycles = max_cycles or _DEFAULT_MAX_CYCLES
        vm = TextVirtualMachine(program=instructions, memory=mem, max_cycles=cycles)

        result = await asyncio.to_thread(vm.run)

        report = [
            "=== [Text Virtual Machine Execution Report] ===",
            f"● 최종 상태: {result['halt_reason']}",
            f"● 총 실행 클럭: {result['cycles_run']} 사이클 (한도: {cycles})",
            f"● 최종 메모리 레지스터: {result['final_memory']}",
        ]
        if result["emitted_messages"]:
            report.append("● 출력 메시지 (EMIT):")
            for msg in result["emitted_messages"]:
                report.append(f"  - {msg}")

        report.append("\n=== [Execution Trace (클럭별 실행 흐름)] ===")
        report.append(result["execution_trace"])

        return "\n".join(report)
