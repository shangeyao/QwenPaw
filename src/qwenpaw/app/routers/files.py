# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, Request
from starlette.responses import FileResponse

from qwenpaw.constant import WORKING_DIR
from ..auth_scope import get_request_agent_scope
from qwenpaw.security.tool_guard.guardians.file_guardian import (
    FilePathToolGuardian,
    _normalize_path,
)

router = APIRouter(prefix="/files", tags=["files"])

_ALLOWED_ROOT: Path = WORKING_DIR.resolve()

# Reuse the FileGuard sensitive path detection for the preview endpoint.
_file_guardian = FilePathToolGuardian()


def _is_preview_outside_workspace_allowed() -> bool:
    """Check ``security.file_guard.allow_preview_outside_workspace``."""
    try:
        from qwenpaw.config import load_config

        return bool(
            load_config().security.file_guard.allow_preview_outside_workspace,
        )
    except Exception:
        return False


def _get_agent_workspace_root(agent_id: str) -> Path | None:
    """Return the resolved workspace directory for one agent."""
    try:
        from qwenpaw.config import load_config

        ref = load_config().agents.profiles.get(agent_id)
        if ref is None:
            return None
        return Path(ref.workspace_dir).expanduser().resolve()
    except Exception:
        return None


def _check_path(
    path: Path,
    *,
    agent_workspace: Path | None = None,
) -> str | None:
    """Return ``None`` when *path* is allowed, or an error reason string.

    When ``allow_preview_outside_workspace`` is enabled, skip the
    WORKING_DIR containment check so that console can preview files
    (e.g. media produced by tools) stored outside the workspace.
    Agent-scoped callers are always limited to their own workspace.
    The sensitive-file guard is **always** enforced.
    """
    resolved = path.resolve()
    # 1. Must not be a FileGuard-sensitive path.
    normalized = _normalize_path(str(resolved))
    # pylint: disable-next=protected-access
    if _file_guardian._is_sensitive(normalized):
        return "SENSITIVE_FILE_BLOCKED"
    # 2. Workspace scope check (skippable via config for admins only).
    if agent_workspace is not None:
        ws_resolved = agent_workspace.resolve()
        if not (
            resolved == ws_resolved or resolved.is_relative_to(ws_resolved)
        ):
            return "FORBIDDEN"
    elif not _is_preview_outside_workspace_allowed():
        if not (
            resolved == _ALLOWED_ROOT or resolved.is_relative_to(_ALLOWED_ROOT)
        ):
            return "OUTSIDE_WORKSPACE"
    return None


@router.api_route(
    "/preview/{filepath:path}",
    methods=["GET", "HEAD"],
    summary="Preview file",
)
async def preview_file(
    filepath: str,
    request: Request,
):
    """Preview file."""
    normalized = unquote(filepath)

    # Normalize /C:/... to C:/... on Windows.
    if (
        len(normalized) >= 4
        and normalized[0] == "/"
        and normalized[2] == ":"
        and normalized[1].isalpha()
    ):
        normalized = normalized[1:]

    path = Path(normalized).expanduser()
    if not path.is_absolute():
        path = Path("/" + normalized)
    path = path.resolve()
    scoped_agent = get_request_agent_scope(request)
    agent_workspace = (
        _get_agent_workspace_root(scoped_agent) if scoped_agent else None
    )
    reason = _check_path(path, agent_workspace=agent_workspace)
    if reason:
        raise HTTPException(status_code=403, detail=reason)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")

    if not os.access(path, os.R_OK):
        raise HTTPException(status_code=500, detail="Permission denied")
    return FileResponse(
        path,
        filename=path.name,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
