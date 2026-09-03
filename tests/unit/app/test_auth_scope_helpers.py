# -*- coding: utf-8 -*-
"""Unit tests for auth_scope helpers."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from qwenpaw.app.auth_scope import (
    is_pool_delete_request,
    require_admin,
)


@pytest.mark.parametrize(
    ("path", "method", "expected"),
    [
        ("/api/skills/pool/demo", "DELETE", True),
        ("/api/agents/a/skills/pool/demo", "DELETE", True),
        ("/api/skills/pool/batch-delete", "POST", True),
        ("/api/agents/a/skills/pool/batch-delete", "POST", True),
        ("/api/skills/pool/demo/config", "DELETE", True),
        ("/api/skills/pool/create", "POST", False),
        ("/api/skills/pool", "GET", False),
    ],
)
def test_is_pool_delete_request(path, method, expected):
    assert is_pool_delete_request(path, method) is expected


def test_require_admin_allows_admin_request():
    request = SimpleNamespace(
        state=SimpleNamespace(auth_role="admin", auth_agent_id=None),
    )
    require_admin(request)


def test_require_admin_rejects_agent_request():
    request = SimpleNamespace(
        state=SimpleNamespace(auth_role="agent", auth_agent_id="agent-a"),
    )
    with pytest.raises(HTTPException) as exc:
        require_admin(request)
    assert exc.value.status_code == 403
