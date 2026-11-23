import asyncio
import os
import subprocess
import sys

from pydantic import BaseModel, Field

from config import EMBEDDED_PYTHON_PATH, EXT_LIB_DIR
from core.models import BaseTool, ToolSchema

_PY_VER = f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

_TIMEOUT = 300.0


class PythonExecutionArgs(BaseModel):
    code: str = Field(..., description="The complete Python code to execute. Always use print() to output results.")
    explanation: str = Field(..., description="Brief Korean description of what the code does. (e.g. '데이터 분석', '수치 계산')")


def _run_subprocess(code: str, env: dict) -> str:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        python_exe = str(EMBEDDED_PYTHON_PATH) if EMBEDDED_PYTHON_PATH.exists() else sys.executable
        result = subprocess.run(
            [python_exe, "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=_TIMEOUT,
            env=env,
            creationflags=creationflags,
        )
        output = []
        if result.stdout:
            output.append(f"--- Stdout ---\n{result.stdout.strip()}")
        if result.stderr:
            output.append(f"--- Stderr ---\n{result.stderr.strip()}")
        if not output:
            return "Execution completed successfully, but there was no output. (Did you forget to use print()?)"
        return "\n\n".join(output)
    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {int(_TIMEOUT)} seconds."
    except Exception as e:
        return f"Error executing Python code: {repr(e)}"


class PythonExecutionTool(BaseTool):
    id = "execute_python"
    name = "execute_python"
    description = (
        "Execute Python code in the local environment and return stdout/stderr. "
        "If you encounter a ModuleNotFoundError, install the package and retry. "
        "This execution is ONE-OFF and STATELESS — define all imports and variables every call. "
        "Always use print() to output results. "
        f"Runtime: {_PY_VER}. "
        "ALWAYS provide the 'explanation' field with a brief Korean description."
    )
    input_schema = PythonExecutionArgs

    def get_tool_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.input_schema.model_json_schema(),
        )

    async def execute(self, code: str, explanation: str = "") -> str:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["PYTHONUSERBASE"] = str(EXT_LIB_DIR)
        return await asyncio.to_thread(_run_subprocess, code, env)
