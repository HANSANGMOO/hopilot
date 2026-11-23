import json
import pytest

from core.errors import McpConfigError
from mcp_infra.config import load_mcp_config


class DescribeLoadMcpConfig:
    # ── Tests ─────────────────────────────────────────────────────────────────

    def it_loads_mcp_config(self, mcp_config):
        config = load_mcp_config(mcp_config)

        assert len(config.servers) == 3
        assert config.errors == {}

    def it_loads_mcp_config_with_env_values(self, mcp_config):
        config = load_mcp_config(mcp_config)

        assert config.servers["server-b"].env == {"MY_KEY": "my-value"}

    def it_loads_empty_mcp_config_when_file_not_found(self, tmp_path):
        config = load_mcp_config(tmp_path / "nonexistent.json")

        assert config.servers == {}
        assert config.errors == {}

    def it_loads_mcp_config_with_placeholder(self, mcp_config_with_placeholder):
        path, template_vars = mcp_config_with_placeholder
        config = load_mcp_config(path, template_vars=template_vars)

        assert config.servers["git"].args == ["mcp-server-git", "--repository", "/some/repo"]
        assert config.errors == {}

    def it_loads_mcp_config_with_unknown_placeholder(self, mcp_config_with_unknown_placeholder):
        path, template_vars = mcp_config_with_unknown_placeholder
        config = load_mcp_config(path, template_vars=template_vars)

        assert "bad-server" in config.errors
        assert "good-server" in config.servers

    def it_raises_on_invalid_json(self, invalid_json_config):
        with pytest.raises(McpConfigError):
            load_mcp_config(invalid_json_config)

    # ── Fixtures ──────────────────────────────────────────────────────────────

    @pytest.fixture
    def mcp_config(self, tmp_path):
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps({
            "servers": {
                "server-a": {"transport": "stdio", "command": "npx", "args": ["-y", "pkg-a"]},
                "server-b": {"transport": "stdio", "command": "uvx", "args": ["pkg-b"], "env": {"MY_KEY": "my-value"}},
                "server-c": {"transport": "sse", "url": "http://localhost:8080/sse"},
            }
        }))
        return path

    @pytest.fixture
    def mcp_config_with_placeholder(self, tmp_path):
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps({
            "servers": {
                "git": {
                    "transport": "stdio",
                    "command": "uvx",
                    "args": ["mcp-server-git", "--repository", "{{GIT_REPO_PATH}}"]
                }
            }
        }))
        return path, {"GIT_REPO_PATH": "/some/repo"}

    @pytest.fixture
    def invalid_json_config(self, tmp_path):
        path = tmp_path / "mcp.json"
        path.write_text('{"servers": {"my-server": {"transport": "stdio", "command": "npx", "args": ["-y",]}}}')
        return path

    @pytest.fixture
    def mcp_config_with_unknown_placeholder(self, tmp_path):
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps({
            "servers": {
                "good-server": {"transport": "stdio", "command": "npx", "args": ["-y", "pkg-a"]},
                "bad-server":  {"transport": "stdio", "command": "uvx", "args": ["{{UNKNOWN_VAR}}"]},
            }
        }))
        return path, {}
