# -*- coding: utf-8 -*-
"""Helpers for agent-scoped web auth on API routes."""
from __future__ import annotations

from fastapi import HTTPException, Request


def get_request_agent_scope(request: Request | None) -> str | None:
    """Return authenticated agent scope, or None for admin/global callers."""
    if request is None:
        return None
    role = getattr(request.state, "auth_role", "admin")
    if role == "agent":
        return getattr(request.state, "auth_agent_id", None)
    return None


def normalize_event_agent_id(agent_id: str | None) -> str:
    return agent_id or "default"


def event_belongs_to_agent(event: dict, agent_id: str) -> bool:
    return normalize_event_agent_id(event.get("agent_id")) == agent_id


def approval_belongs_to_agent(pending, agent_id: str) -> bool:
    """Return whether a pending approval belongs to the scoped agent."""
    owner_agent_id = getattr(pending, "owner_agent_id", None)
    if owner_agent_id == agent_id:
        return True
    return getattr(pending, "agent_id", None) == agent_id


def require_agent_event_access(request: Request, event: dict) -> None:
    scoped_agent = get_request_agent_scope(request)
    if scoped_agent and not event_belongs_to_agent(event, scoped_agent):
        raise HTTPException(
            status_code=403,
            detail="Forbidden for this agent",
        )


def require_agent_approval_access(request: Request, pending) -> None:
    scoped_agent = get_request_agent_scope(request)
    if scoped_agent and not approval_belongs_to_agent(pending, scoped_agent):
        raise HTTPException(
            status_code=403,
            detail="Forbidden for this agent",
        )


def require_admin(request: Request | None) -> None:
    """Reject agent-scoped users for admin-only operations."""
    if get_request_agent_scope(request):
        raise HTTPException(
            status_code=403,
            detail="This operation requires an admin account",
        )


def is_pool_delete_request(path: str, method: str) -> bool:
    """Return whether the request deletes skill-pool content."""
    method = method.upper()
    if method not in {"DELETE", "POST"}:
        return False
    marker = "/skills/pool/"
    idx = path.find(marker)
    if idx == -1:
        return path.endswith("/skills/pool/batch-delete") and method == "POST"
    suffix = path[idx + len(marker) :]
    if method == "DELETE":
        return True
    return suffix == "batch-delete" or suffix.startswith("batch-delete")
