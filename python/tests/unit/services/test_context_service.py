import logging
import pytest
from pathlib import Path

from core.models import ContextPaths
from services.context_service import ContextService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def default_paths(tmp_path):
    return ContextPaths(
        static=tmp_path / "default" / "static.md",
        dynamic=tmp_path / "default" / "dynamic.jsonl",
    )

@pytest.fixture
def project_paths(tmp_path):
    workspace = tmp_path / "my_project"
    return ContextPaths(
        static=workspace / ".hopilot" / "context" / "static.md",
        dynamic=workspace / ".hopilot" / "context" / "dynamic.jsonl",
    )

@pytest.fixture
def service(default_paths):
    return ContextService(default=default_paths)


# ── Tests ─────────────────────────────────────────────────────────────────────

class DescribeContextService:
    class DescribeRegister:
        def it_creates_context_directory(self, service, tmp_path):
            workspace = tmp_path / "my_project"
            service.register("proj_001", workspace)
            assert (workspace / ".hopilot" / "context").is_dir()

        def it_creates_static_and_dynamic_files(self, service, tmp_path):
            workspace = tmp_path / "my_project"
            service.register("proj_001", workspace)
            assert (workspace / ".hopilot" / "context" / "static.md").exists()
            assert (workspace / ".hopilot" / "context" / "dynamic.jsonl").exists()

        def it_registers_project_id_and_workspace(self, service, tmp_path):
            workspace = tmp_path / "my_project"
            service.register("proj_001", workspace)
            assert "proj_001" in service._registry

    class DescribeUnregister:
        def it_unregisters_project_id(self, service, tmp_path):
            workspace = tmp_path / "my_project"
            service.register("proj_001", workspace)
            service.unregister("proj_001")
            assert "proj_001" not in service._registry

        def it_ignores_unregistered_project_id(self, service, caplog):
            with caplog.at_level(logging.WARNING):
                service.unregister("nonexistent")
            assert any("nonexistent" in msg for msg in caplog.messages)

    class DescribeResolve:
        def it_returns_default_dynamic_when_project_id_is_none(self, service, default_paths):
            ctx = service.resolve(None)
            assert ctx.dynamic == default_paths.dynamic

        def it_returns_project_dynamic_when_project_is_registered(self, service, tmp_path, project_paths):
            service.register("proj_001", tmp_path / "my_project")
            ctx = service.resolve("proj_001")
            assert ctx.dynamic == project_paths.dynamic

        def it_returns_default_static_when_project_id_is_none(self, service, default_paths):
            default_paths.static.parent.mkdir(parents=True, exist_ok=True)
            default_paths.static.write_text("default content", encoding="utf-8")
            ctx = service.resolve(None)
            assert ctx.static == "default content"

        def it_returns_merged_static_when_project_is_registered(self, service, default_paths, tmp_path, project_paths):
            default_paths.static.parent.mkdir(parents=True, exist_ok=True)
            default_paths.static.write_text("default content", encoding="utf-8")
            service.register("proj_001", tmp_path / "my_project")
            project_paths.static.write_text("project content", encoding="utf-8")
            ctx = service.resolve("proj_001")
            assert "default content" in ctx.static
            assert "project content" in ctx.static

        def it_returns_default_context_when_project_id_is_not_registered(self, service, default_paths, caplog):
            default_paths.static.parent.mkdir(parents=True, exist_ok=True)
            default_paths.static.write_text("default content", encoding="utf-8")
            with caplog.at_level(logging.WARNING):
                ctx = service.resolve("nonexistent")
            assert ctx.dynamic == default_paths.dynamic
            assert ctx.static == "default content"
            assert any("nonexistent" in msg for msg in caplog.messages)
