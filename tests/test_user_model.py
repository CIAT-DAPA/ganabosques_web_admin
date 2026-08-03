from types import SimpleNamespace

from flask import session

from src.models.User import User


def test_user_extracts_roles_and_filters_system_roles():
    user_data = {
        "sub": "user-1",
        "preferred_username": "tester",
        "roles": ["offline_access", "admin"],
        "realm_access": {"roles": ["adminsuper", "uma_authorization"]},
        "resource_access": {"account": {"roles": ["viewer"]}},
    }

    user = User(user_data)

    assert "offline_access" not in user.roles
    assert "uma_authorization" not in user.roles
    assert "admin" in user.roles
    assert "adminsuper" in user.roles
    assert "viewer" in user.roles
    assert user.is_admin() is True
    assert user.is_super_admin() is True


def test_authenticate_oauth_persists_session(flask_app):
    with flask_app.test_request_context("/"):
        token_data = {
            "access_token": "access-123",
            "refresh_token": "refresh-123",
            "id_token": "id-123",
        }
        user_info = {"sub": "1", "preferred_username": "alice", "roles": ["admin"]}

        user = User.authenticate_oauth(token_data, user_info)

        assert user is not None
        assert session["access_token"] == "access-123"
        assert session["refresh_token"] == "refresh-123"
        assert session["id_token"] == "id-123"
        assert session["user_data"]["preferred_username"] == "alice"


def test_get_returns_user_when_id_matches(flask_app):
    with flask_app.test_request_context("/"):
        session["user_data"] = {"sub": "abc", "preferred_username": "alice", "roles": []}

        user = User.get("abc")

        assert user is not None
        assert user.username == "alice"


def test_get_returns_none_when_id_does_not_match(flask_app):
    with flask_app.test_request_context("/"):
        session["user_data"] = {"sub": "abc", "preferred_username": "alice", "roles": []}

        assert User.get("xyz") is None


def test_validate_token_uses_oauth_extension(flask_app):
    with flask_app.test_request_context("/"):
        session["access_token"] = "token-123"
        user = User({"sub": "1", "preferred_username": "alice", "roles": ["admin"]})

        class FakeOAuthService:
            def validate_token(self, token):
                return token == "token-123"

        flask_app.extensions = {"oauth_service": FakeOAuthService()}

        assert user.validate_token() is True


def test_validate_token_returns_false_without_token(flask_app):
    with flask_app.test_request_context("/"):
        user = User({"sub": "1", "preferred_username": "alice", "roles": []})

        assert user.validate_token() is False
