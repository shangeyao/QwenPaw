# -*- coding: utf-8 -*-
"""Unit tests for agent-scoped auth middleware access rules."""
from __future__ import annotations

from types import SimpleNamespace

from qwenpaw.app.auth import AuthMiddleware


def _request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        method=method,
        headers=headers or {},
    )


def _agent_principal(agent_id: str = "agent-a") -> dict:
    return {
        "username": "agent-user",
        "role": "agent",
        "agent_id": agent_id,
    }


def test_agent_scope_allows_file_preview_get():
    request = _request("/api/files/preview/tmp/report.pdf")
    assert AuthMiddleware._is_agent_scope_allowed(request, _agent_principal())


def test_agent_scope_allows_file_preview_head():
    request = _request(
        "/api/files/preview/tmp/report.pdf",
        method="HEAD",
    )
    assert AuthMiddleware._is_agent_scope_allowed(request, _agent_principal())


def test_agent_scope_blocks_file_preview_post():
    request = _request(
        "/api/files/preview/tmp/report.pdf",
        method="POST",
    )
    assert not AuthMiddleware._is_agent_scope_allowed(
        request,
        _agent_principal(),
    )


def test_agent_scope_still_blocks_unrelated_global_api():
    request = _request("/api/providers")
    assert not AuthMiddleware._is_agent_scope_allowed(
        request,
        _agent_principal(),
    )


def test_agent_scope_blocks_scoped_pool_delete():
    request = _request(
        "/api/agents/agent-a/skills/pool/demo-skill",
        method="DELETE",
    )
    assert not AuthMiddleware._is_agent_scope_allowed(
        request,
        _agent_principal("agent-a"),
    )


def test_agent_scope_blocks_scoped_pool_batch_delete():
    request = _request(
        "/api/agents/agent-a/skills/pool/batch-delete",
        method="POST",
    )
    assert not AuthMiddleware._is_agent_scope_allowed(
        request,
        _agent_principal("agent-a"),
    )


def test_agent_scope_allows_scoped_workspace_skill_delete():
    request = _request(
        "/api/agents/agent-a/skills/local-skill",
        method="DELETE",
    )
    assert AuthMiddleware._is_agent_scope_allowed(
        request,
        _agent_principal("agent-a"),
    )
