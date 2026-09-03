# -*- coding: utf-8 -*-
"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..auth import (
    AuthPrincipal,
    authenticate,
    create_agent_account,
    delete_agent_account,
    get_account_role,
    has_registered_users,
    is_auth_enabled,
    list_web_accounts,
    register_user,
    revoke_all_tokens,
    revoke_token,
    update_agent_account,
    update_agent_credentials_self,
    update_credentials,
    verify_token,
    verify_token_principal,
    resolve_client_ip,
)
from ..rate_limiter import rate_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _require_admin(request: Request) -> AuthPrincipal:
    """Ensure the caller is an authenticated admin account."""
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    principal = verify_token_principal(token) if token else None
    if principal is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if principal.get("role") == "agent":
        raise HTTPException(
            status_code=403,
            detail="This operation requires an admin account",
        )
    return principal


class WebAccountSummary(BaseModel):
    username: str
    role: str
    agent_id: str | None = None


class WebAccountListResponse(BaseModel):
    accounts: list[WebAccountSummary]


class CreateWebAccountRequest(BaseModel):
    username: str
    password: str
    role: str = "agent"
    agent_id: str | None = None


class UpdateWebAccountRequest(BaseModel):
    new_username: str | None = None
    password: str | None = None
    agent_id: str | None = None
    current_password: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str
    expires_in: int | None = (
        None  # Token expiry in seconds, -1/0 for permanent
    )


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str = "admin"
    agent_id: str | None = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    expires_in: int | None = (
        None  # Token expiry in seconds, -1/0 for permanent
    )


class AuthStatusResponse(BaseModel):
    enabled: bool
    has_users: bool


@router.post("/login")
async def login(request: Request, req: LoginRequest):
    """Authenticate with username and password.

    Optional `expires_in` field:
    - Positive integer: token expires in N seconds
    - 0 or -1: permanent token (100 years)
    - None/omitted: default 7 days
    """
    if not is_auth_enabled():
        return LoginResponse(token="", username="")

    # Get client IP for rate limiting
    client_ip = resolve_client_ip(request)

    # Check if user account is locked
    if rate_limiter.is_user_locked(req.username):
        raise HTTPException(
            status_code=423,
            detail="Account temporarily locked. Please try again later",
        )

    # Check if IP is locked or rate-limited
    if rate_limiter.is_ip_locked(client_ip):
        raise HTTPException(
            status_code=423,
            detail="Too many login attempts. Please try again later",
        )

    if rate_limiter.is_ip_rate_limited(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down",
        )

    # Attempt authentication
    token = authenticate(req.username, req.password, req.expires_in)
    if token is None:
        # Record failed attempt
        rate_limiter.record_login_attempt(
            client_ip,
            req.username,
            success=False,
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    # Record successful attempt
    rate_limiter.record_login_attempt(client_ip, req.username, success=True)

    principal = verify_token_principal(token)
    return LoginResponse(
        token=token,
        username=req.username,
        role=principal.get("role", "admin") if principal else "admin",
        agent_id=principal.get("agent_id") if principal else None,
    )


@router.post("/register")
async def register(req: RegisterRequest):
    """Register the single user account (only allowed once).

    Optional `expires_in` field:
    - Positive integer: token expires in N seconds
    - 0 or -1: permanent token (100 years)
    - None/omitted: default 7 days
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="User already registered",
        )

    if not req.username.strip() or not req.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Username and password are required",
        )

    token = register_user(req.username.strip(), req.password, req.expires_in)
    if token is None:
        raise HTTPException(
            status_code=409,
            detail="Registration failed",
        )

    return LoginResponse(token=token, username=req.username.strip())


@router.get("/status")
async def auth_status():
    """Check if authentication is enabled and whether a user exists."""
    return AuthStatusResponse(
        enabled=is_auth_enabled(),
        has_users=has_registered_users(),
    )


@router.get("/verify")
async def verify(request: Request):
    """Verify that the caller's Bearer token is still valid."""
    if not is_auth_enabled():
        return {"valid": True, "username": ""}

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")

    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    principal = verify_token_principal(token)
    return {
        "valid": True,
        "username": username,
        "role": principal.get("role", "admin") if principal else "admin",
        "agent_id": principal.get("agent_id") if principal else None,
    }


class UpdateProfileRequest(BaseModel):
    current_password: str
    new_username: str | None = None
    new_password: str | None = None
    expires_in: int | None = (
        None  # Token expiry in seconds, -1/0 for permanent
    )


@router.post("/update-profile")
async def update_profile(req: UpdateProfileRequest, request: Request):
    """Update username and/or password for the authenticated user."""
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    if not has_registered_users():
        raise HTTPException(
            status_code=403,
            detail="No user registered",
        )

    # Verify caller is authenticated
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    principal = verify_token_principal(caller_token) if caller_token else None
    if principal is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not req.new_username and not req.new_password:
        raise HTTPException(
            status_code=400,
            detail="Nothing to update",
        )

    if req.new_username is not None and not req.new_username.strip():
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty",
        )

    if req.new_password is not None and not req.new_password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty",
        )

    if principal.get("role") == "agent":
        try:
            token = update_agent_credentials_self(
                principal["username"],
                current_password=req.current_password,
                new_username=req.new_username,
                new_password=req.new_password,
                expiry_seconds=req.expires_in,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="Current password is incorrect",
            )
        next_principal = verify_token_principal(token)
        next_username = (
            next_principal.get("username")
            if next_principal
            else principal.get("username", "")
        )
        return LoginResponse(
            token=token,
            username=next_username,
            role="agent",
            agent_id=(
                next_principal.get("agent_id")
                if next_principal
                else principal.get("agent_id")
            ),
        )

    token = update_credentials(
        current_password=req.current_password,
        new_username=req.new_username,
        new_password=req.new_password,
        expiry_seconds=req.expires_in,
    )
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect",
        )

    username = req.new_username.strip() if req.new_username else ""
    return LoginResponse(token=token, username=username)


class RevokeTokenRequest(BaseModel):
    token: str | None = (
        None  # Optional: revoke specific token, or current if omitted
    )


@router.post("/revoke-token")
async def revoke_single_token(req: RevokeTokenRequest, request: Request):
    """Revoke a single token by adding it to the blacklist.

    If `token` is provided in the request body, revokes that token.
    If `token` is omitted, revokes the token used for authentication
    (current token).

    This allows you to:
    - Revoke a leaked token from another device
    - Logout from the current session
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    # Get current token for authentication
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not caller_token or verify_token(caller_token) is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Determine which token to revoke
    token_to_revoke = req.token if req.token else caller_token
    is_current_token = token_to_revoke == caller_token

    success = revoke_token(token_to_revoke)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke token",
        )

    message = (
        "Current token has been revoked. Please login again."
        if is_current_token
        else "Specified token has been revoked."
    )

    return {
        "message": message,
        "revoked": True,
        "revoked_current_token": is_current_token,
    }


@router.post("/revoke-all-tokens")
async def revoke_all_sessions(request: Request):
    """Revoke all existing tokens by rotating the JWT secret.

    This endpoint requires authentication. After calling this endpoint,
    all previously issued tokens will be invalidated, and you will need
    to login again to get a new token.

    This is more efficient than revoking tokens individually when you
    want to invalidate all sessions (e.g., password reset, security incident).
    """
    if not is_auth_enabled():
        raise HTTPException(
            status_code=403,
            detail="Authentication is not enabled",
        )

    # Verify caller is authenticated
    auth_header = request.headers.get("Authorization", "")
    caller_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not caller_token or verify_token(caller_token) is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    success = revoke_all_tokens()
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to revoke tokens",
        )

    return {
        "message": "All tokens have been revoked. Please login again.",
        "revoked": True,
    }


@router.get("/accounts", response_model=WebAccountListResponse)
async def list_accounts(request: Request) -> WebAccountListResponse:
    """List all web login accounts (admin only)."""
    _require_admin(request)
    try:
        accounts = list_web_accounts()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return WebAccountListResponse(
        accounts=[WebAccountSummary(**account) for account in accounts],
    )


@router.post("/accounts", response_model=WebAccountSummary, status_code=201)
async def create_account(
    request: Request,
    req: CreateWebAccountRequest,
) -> WebAccountSummary:
    """Create a new agent-scoped web login account (admin only)."""
    _require_admin(request)

    role = req.role.strip().lower()
    if role != "agent":
        raise HTTPException(
            status_code=400,
            detail="Only agent accounts can be created here",
        )
    if not req.agent_id or not req.agent_id.strip():
        raise HTTPException(status_code=400, detail="Agent is required")
    if not req.username.strip() or not req.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Username and password are required",
        )

    try:
        create_agent_account(
            req.username.strip(),
            req.password,
            req.agent_id.strip(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return WebAccountSummary(
        username=req.username.strip(),
        role="agent",
        agent_id=req.agent_id.strip(),
    )


@router.put("/accounts/{username}", response_model=WebAccountSummary)
async def update_account(
    request: Request,
    username: str,
    req: UpdateWebAccountRequest,
) -> WebAccountSummary:
    """Update a web login account (admin only)."""
    _require_admin(request)

    role = get_account_role(username)
    if role is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if not req.new_username and not req.password and req.agent_id is None:
        raise HTTPException(status_code=400, detail="Nothing to update")

    if role == "admin":
        if not req.current_password:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Current password is required to update the admin account"
                ),
            )
        token = update_credentials(
            current_password=req.current_password,
            new_username=req.new_username,
            new_password=req.password,
        )
        if token is None:
            raise HTTPException(
                status_code=401,
                detail="Current password is incorrect",
            )
        data = list_web_accounts()
        admin = next((a for a in data if a["role"] == "admin"), None)
        if admin is None:
            raise HTTPException(
                status_code=500,
                detail="Admin account missing",
            )
        return WebAccountSummary(**admin)

    try:
        update_agent_account(
            username,
            new_username=req.new_username,
            password=req.password,
            agent_id=req.agent_id,
        )
    except ValueError as exc:
        status = 404 if str(exc) == "Account not found" else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    next_username = (
        req.new_username.strip()
        if req.new_username and req.new_username.strip()
        else username
    )
    next_agent_id = (
        req.agent_id.strip() if req.agent_id and req.agent_id.strip() else None
    )
    if next_agent_id is None:
        for account in list_web_accounts():
            if account["username"] == next_username:
                next_agent_id = account.get("agent_id")
                break

    return WebAccountSummary(
        username=next_username,
        role="agent",
        agent_id=next_agent_id,
    )


@router.delete("/accounts/{username}")
async def delete_account(request: Request, username: str) -> dict:
    """Delete an agent-scoped web login account (admin only)."""
    _require_admin(request)

    role = get_account_role(username)
    if role is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if role == "admin":
        raise HTTPException(
            status_code=400,
            detail="The admin account cannot be deleted",
        )

    try:
        delete_agent_account(username)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"success": True, "username": username}
