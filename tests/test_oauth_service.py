from types import SimpleNamespace

import src.services.oauth_service as oauth_module
from src.services.oauth_service import OAuthService


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeOAuthClient:
    def __init__(self):
        self.last_redirect = None

    def authorize_redirect(self, redirect_uri):
        self.last_redirect = redirect_uri
        return {"redirect": redirect_uri}

    def authorize_access_token(self):
        return {"access_token": "token"}

    def userinfo(self, token):
        return {"preferred_username": "alice", "sub": "1", "realm_access": {"roles": ["admin"]}}

    def parse_id_token(self, token):
        return {"preferred_username": "alice"}


class FakeOAuthEngine:
    def __init__(self):
        self.init_calls = 0
        self.register_kwargs = None

    def init_app(self, app):
        self.init_calls += 1

    def register(self, **kwargs):
        self.register_kwargs = kwargs
        return FakeOAuthClient()


def test_init_app_registers_keycloak(flask_app):
    flask_app.config.update(
        KEYCLOAK_SERVER_URL="https://kc.example.com",
        KEYCLOAK_REALM="realm-demo",
        KEYCLOAK_CLIENT_ID="client-id",
        KEYCLOAK_CLIENT_SECRET="secret",
    )

    service = OAuthService()
    fake_oauth = FakeOAuthEngine()
    service.oauth = fake_oauth

    service.init_app(flask_app)

    assert service.keycloak is not None
    assert fake_oauth.init_calls == 1
    assert fake_oauth.register_kwargs["authorize_url"].endswith("/protocol/openid-connect/auth")


def test_get_authorization_url_requires_initialized_client():
    service = OAuthService()

    try:
        service.get_authorization_url("http://localhost/callback")
        assert False, "Expected RuntimeError when keycloak is not initialized"
    except RuntimeError:
        assert True


def test_exchange_code_for_token_returns_none_on_failure():
    service = OAuthService()
    service.keycloak = SimpleNamespace(authorize_access_token=lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert service.exchange_code_for_token() is None


def test_get_auth_headers_uses_explicit_token():
    headers = OAuthService.get_auth_headers("abc123")
    assert headers == {"Authorization": "Bearer abc123"}


def test_get_auth_headers_uses_session_token(flask_app):
    with flask_app.test_request_context("/"):
        from flask import session

        session["access_token"] = "from-session"
        headers = OAuthService.get_auth_headers()

        assert headers == {"Authorization": "Bearer from-session"}


def test_logout_url_builds_query(flask_app):
    flask_app.config.update(
        KEYCLOAK_SERVER_URL="https://kc.example.com",
        KEYCLOAK_REALM="realm-demo",
    )

    service = OAuthService()

    with flask_app.app_context():
        url = service.logout_url("https://app.example.com/bye", "id-token")

    assert "id_token_hint=id-token" in url
    assert "post_logout_redirect_uri=https://app.example.com/bye" in url


def test_validate_token_with_api_uses_default_base(monkeypatch, flask_app):
    flask_app.config.update(API_BASE_URL="")

    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResponse(status_code=200, payload={"valid": True})

    monkeypatch.setattr(oauth_module.requests, "get", fake_get)

    service = OAuthService()

    with flask_app.app_context():
        result = service.validate_token_with_api("token-abc")

    assert result == {"valid": True}
    assert captured["url"].endswith("/auth/token/validate")
    assert captured["headers"]["Authorization"] == "Bearer token-abc"


def test_get_user_info_returns_userinfo_from_client(monkeypatch, flask_app):
    flask_app.config.update(
        KEYCLOAK_SERVER_URL="https://kc.example.com",
        KEYCLOAK_REALM="realm-demo",
    )

    service = OAuthService()
    service.keycloak = FakeOAuthClient()

    monkeypatch.setattr(service, "_enrich_user_info", lambda info, token: {**info, "enriched": True})

    with flask_app.app_context():
        user_info = service.get_user_info({"access_token": "abc"})

    assert user_info["preferred_username"] == "alice"
    assert user_info["enriched"] is True
