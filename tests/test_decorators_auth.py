from types import SimpleNamespace

from flask import Flask

from src.decorators.auth import login_required_only, token_required
import src.decorators.auth as auth_module


def _build_app():
    app = Flask(__name__)
    app.config.update(SECRET_KEY="test", TESTING=True)

    @app.route("/login")
    def login_endpoint():
        return "login"

    app.add_url_rule("/home-login", endpoint="home_bp.login", view_func=login_endpoint)

    @app.route("/protected-token")
    @token_required
    def protected_token():
        return "token-ok"

    @app.route("/protected-login")
    @login_required_only
    def protected_login():
        return "login-ok"

    return app


def test_token_required_redirects_when_unauthenticated(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(auth_module, "current_user", SimpleNamespace(is_authenticated=False))

    client = app.test_client()
    response = client.get("/protected-token", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/home-login")


def test_token_required_allows_authenticated(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(auth_module, "current_user", SimpleNamespace(is_authenticated=True))

    client = app.test_client()
    response = client.get("/protected-token")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "token-ok"


def test_login_required_only_redirects_when_unauthenticated(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(auth_module, "current_user", SimpleNamespace(is_authenticated=False))

    client = app.test_client()
    response = client.get("/protected-login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/home-login")


def test_login_required_only_allows_authenticated(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(auth_module, "current_user", SimpleNamespace(is_authenticated=True))

    client = app.test_client()
    response = client.get("/protected-login")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "login-ok"
