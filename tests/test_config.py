import importlib
import sys


def _reload_config_module():
    sys.modules.pop("config", None)
    return importlib.import_module("config")


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("HOST", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)

    config_module = _reload_config_module()

    assert config_module.config["PORT"] == 5000
    assert config_module.config["HOST"] == "0.0.0.0"
    assert config_module.config["DEBUG"] is False
    assert config_module.config["API_BASE_URL"] == "http://localhost:8000"


def test_keycloak_derived_urls(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_SERVER_URL", "https://kc.example.com")
    monkeypatch.setenv("KEYCLOAK_REALM", "demo")

    config_module = _reload_config_module()

    assert config_module.config["KEYCLOAK_AUTHORIZATION_URL"] == (
        "https://kc.example.com/realms/demo/protocol/openid-connect/auth"
    )
    assert config_module.config["KEYCLOAK_TOKEN_URL"] == (
        "https://kc.example.com/realms/demo/protocol/openid-connect/token"
    )
    assert config_module.config["KEYCLOAK_USERINFO_URL"] == (
        "https://kc.example.com/realms/demo/protocol/openid-connect/userinfo"
    )
