# -*- coding: utf-8 -*-
"""Unit tests for agent self-service credential updates."""
# pylint: disable=protected-access
from __future__ import annotations

import json

import pytest

from qwenpaw.app import auth as auth_module


def _write_auth(auth_file, data: dict) -> None:
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture(name="auth_file")
def auth_file_fixture(monkeypatch, tmp_path):
    path = tmp_path / "auth.json"
    monkeypatch.setattr(auth_module, "AUTH_FILE", path)
    return path


def test_update_agent_credentials_self_changes_password(auth_file):
    pw_hash, salt = auth_module._hash_password("old-pass")
    _write_auth(
        auth_file,
        {
            "jwt_secret": "test-secret",
            "agent_users": {
                "agent-a": {
                    "username": "agent-user",
                    "password_hash": pw_hash,
                    "password_salt": salt,
                },
            },
        },
    )

    token = auth_module.update_agent_credentials_self(
        "agent-user",
        current_password="old-pass",
        new_password="new-pass",
    )

    assert token is not None
    principal = auth_module.verify_token_principal(token)
    assert principal == {
        "username": "agent-user",
        "role": "agent",
        "agent_id": "agent-a",
    }

    data = json.loads(auth_file.read_text(encoding="utf-8"))
    updated = data["agent_users"]["agent-a"]
    assert updated["username"] == "agent-user"
    assert auth_module.verify_password(
        "new-pass",
        updated["password_hash"],
        updated["password_salt"],
    )


def test_update_agent_credentials_self_changes_username(auth_file):
    pw_hash, salt = auth_module._hash_password("secret")
    _write_auth(
        auth_file,
        {
            "jwt_secret": "test-secret",
            "agent_users": {
                "agent-a": {
                    "username": "old-name",
                    "password_hash": pw_hash,
                    "password_salt": salt,
                },
            },
        },
    )

    token = auth_module.update_agent_credentials_self(
        "old-name",
        current_password="secret",
        new_username="new-name",
    )

    assert token is not None
    principal = auth_module.verify_token_principal(token)
    assert principal["username"] == "new-name"
    assert principal["agent_id"] == "agent-a"

    data = json.loads(auth_file.read_text(encoding="utf-8"))
    assert data["agent_users"]["agent-a"]["username"] == "new-name"


def test_update_agent_credentials_self_rejects_wrong_password(auth_file):
    pw_hash, salt = auth_module._hash_password("secret")
    _write_auth(
        auth_file,
        {
            "jwt_secret": "test-secret",
            "agent_users": {
                "agent-a": {
                    "username": "agent-user",
                    "password_hash": pw_hash,
                    "password_salt": salt,
                },
            },
        },
    )

    token = auth_module.update_agent_credentials_self(
        "agent-user",
        current_password="wrong",
        new_password="new-pass",
    )
    assert token is None


def test_update_agent_credentials_self_rejects_duplicate_username(auth_file):
    pw_hash, salt = auth_module._hash_password("secret")
    other_hash, other_salt = auth_module._hash_password("other")
    _write_auth(
        auth_file,
        {
            "jwt_secret": "test-secret",
            "agent_users": {
                "agent-a": {
                    "username": "agent-a-user",
                    "password_hash": pw_hash,
                    "password_salt": salt,
                },
                "agent-b": {
                    "username": "taken-name",
                    "password_hash": other_hash,
                    "password_salt": other_salt,
                },
            },
        },
    )

    with pytest.raises(ValueError, match="Username already exists"):
        auth_module.update_agent_credentials_self(
            "agent-a-user",
            current_password="secret",
            new_username="taken-name",
        )
