"""
MCP 설정 파일(%LOCALAPPDATA%/hopilot/mcp.json) 의 Pydantic 스키마 및 로더입니다.

mcp.json 안에서 {{VAR}} 형식의 플레이스홀더를 사용하면
config.py 의 MCP_TEMPLATE_VARS 값으로 자동 치환됩니다.

mcp.json 예시:
{
  "servers": {
    "filesystem": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "sqlite": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "{{SQLITE_DB_PATH}}"]
    },
    "memory": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": { "MEMORY_FILE_PATH": "{{MEMORY_FILE_PATH}}" }
    },
    "sequential-thinking": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]
    },
    "my-sse-server": {
      "transport": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
"""
import json
import re
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from pathlib import Path

from core.errors import McpConfigError
from core.models import McpTemplateVars


class StdioServerConfig(BaseModel):
    transport: Literal["stdio"]
    command: str
    args: List[str] = []
    env: Optional[Dict[str, str]] = None


class SseServerConfig(BaseModel):
    transport: Literal["sse"]
    url: str


McpServerConfig = StdioServerConfig | SseServerConfig


class McpConfig(BaseModel):
    servers: Dict[str, McpServerConfig] = {}
    errors: Dict[str, str] = {}


def _resolve_template(text: str, template_vars: McpTemplateVars) -> str:
    """문자열 안의 {{VAR}} 플레이스홀더를 template_vars 값으로 치환합니다."""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        if key not in template_vars:
            raise KeyError(f"mcp.json 플레이스홀더 '{{{{ {key} }}}}' 에 대응하는 값이 없습니다.")
        return template_vars[key]
    return re.sub(r"\{\{(\w+)\}\}", replacer, text)


def load_mcp_config(path: Path, template_vars: Optional[McpTemplateVars] = None) -> McpConfig:
    """
    mcp.json 을 읽어 McpConfig 를 반환합니다.
    - 파일이 없으면 빈 설정을 반환합니다.
    - {{VAR}} 플레이스홀더는 서버별로 치환되며, 실패한 서버는 errors 필드에 담깁니다.
    """
    if not path.exists():
        return McpConfig()

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise McpConfigError(f"mcp.json 파일을 읽을 수 없습니다: {e}") from e

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise McpConfigError(f"mcp.json 파싱에 실패했습니다: {e}") from e

    vars_ = template_vars or {}
    resolved_servers: Dict[str, dict] = {}
    errors: Dict[str, str] = {}

    for name, cfg in raw.get("servers", {}).items():
        try:
            resolved_servers[name] = json.loads(_resolve_template(json.dumps(cfg), vars_))
        except KeyError as e:
            errors[name] = str(e)
        except Exception as e:
            errors[name] = str(e)

    return McpConfig.model_validate({"servers": resolved_servers, "errors": errors})
