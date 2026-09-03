# -*- coding: utf-8 -*-
"""Unit tests for file preview path scoping."""
from __future__ import annotations

from pathlib import Path

from qwenpaw.app.routers.files import _check_path


def test_check_path_allows_file_inside_agent_workspace(tmp_path):
    workspace = tmp_path / "agent_ws"
    workspace.mkdir()
    target = workspace / "media" / "report.pdf"
    target.parent.mkdir()
    target.write_bytes(b"pdf")

    assert _check_path(target, agent_workspace=workspace) is None


def test_check_path_blocks_file_outside_agent_workspace(tmp_path):
    workspace = tmp_path / "agent_a"
    other = tmp_path / "agent_b"
    workspace.mkdir()
    other.mkdir()
    target = other / "secret.pdf"
    target.write_bytes(b"pdf")

    assert _check_path(target, agent_workspace=workspace) == "FORBIDDEN"


def test_check_path_admin_uses_working_dir_scope(tmp_path, monkeypatch):
    working_dir = tmp_path / "working"
    working_dir.mkdir()
    inside = working_dir / "shared.txt"
    inside.write_text("ok", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("no", encoding="utf-8")

    monkeypatch.setattr(
        "qwenpaw.app.routers.files._ALLOWED_ROOT",
        working_dir.resolve(),
    )
    monkeypatch.setattr(
        "qwenpaw.app.routers.files._is_preview_outside_workspace_allowed",
        lambda: False,
    )

    assert _check_path(inside) is None
    assert _check_path(outside) == "OUTSIDE_WORKSPACE"
