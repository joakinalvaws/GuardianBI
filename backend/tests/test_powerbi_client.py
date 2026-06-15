"""Tests de PowerBIClient con httpx mockeado (no existe tenant real — ADR-005)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.scanner.powerbi_client import API_BASE, SCOPE, PowerBIClient, PowerBINoConfigurado

TENANT = "11111111-aaaa-bbbb-cccc-222222222222"
WORKSPACE = "33333333-dddd-eeee-ffff-444444444444"
DATASET = "55555555-aaaa-bbbb-cccc-666666666666"


def _respuesta(cuerpo: dict) -> MagicMock:
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = cuerpo
    return r


def _token_respuesta() -> MagicMock:
    return _respuesta({"access_token": "tok-123", "expires_in": 3600})


@pytest.fixture
def configurado(monkeypatch) -> None:
    monkeypatch.setattr(settings, "powerbi_tenant_id", TENANT)
    monkeypatch.setattr(settings, "powerbi_client_id", "app-id")
    monkeypatch.setattr(settings, "powerbi_client_secret", "app-secret")
    monkeypatch.setattr(settings, "powerbi_workspace_id", WORKSPACE)
    monkeypatch.setattr(settings, "powerbi_username", "guardian@tenant.onmicrosoft.com")
    monkeypatch.setattr(settings, "powerbi_password", "test-password")


def test_sin_configurar_levanta_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "powerbi_tenant_id", "")
    monkeypatch.setattr(settings, "powerbi_client_id", "")
    monkeypatch.setattr(settings, "powerbi_username", "")

    with pytest.raises(PowerBINoConfigurado, match="POWERBI_TENANT_ID"):
        PowerBIClient()


def test_token_por_ropc(configurado) -> None:
    filas = [{"[valor]": 39845.3}]
    mock_post = MagicMock(
        side_effect=[
            _token_respuesta(),
            _respuesta({"results": [{"tables": [{"rows": filas}]}]}),
        ]
    )

    with patch("app.scanner.powerbi_client.httpx.post", mock_post):
        resultado = PowerBIClient().execute_dax(DATASET, 'EVALUATE ROW("valor", [x])')

    assert resultado == filas
    # 1er POST: token contra Entra ID — ROPC flow con usuario y contraseña
    url_token, = mock_post.call_args_list[0].args
    assert url_token == f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
    data = mock_post.call_args_list[0].kwargs["data"]
    assert data["grant_type"] == "password"
    assert data["client_id"] == "app-id"
    assert data["client_secret"] == "app-secret"
    assert data["username"] == "guardian@tenant.onmicrosoft.com"
    assert data["password"] == "test-password"
    assert data["scope"] == SCOPE
    # 2do POST: executeQueries con el bearer y la consulta DAX
    url_query, = mock_post.call_args_list[1].args
    assert url_query == f"{API_BASE}/groups/{WORKSPACE}/datasets/{DATASET}/executeQueries"
    kwargs = mock_post.call_args_list[1].kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer tok-123"
    assert kwargs["json"] == {"queries": [{"query": 'EVALUATE ROW("valor", [x])'}]}


def test_token_se_cachea_entre_llamadas(configurado) -> None:
    query_ok = lambda: _respuesta({"results": [{"tables": [{"rows": []}]}]})  # noqa: E731
    mock_post = MagicMock(side_effect=[_token_respuesta(), query_ok(), query_ok()])

    with patch("app.scanner.powerbi_client.httpx.post", mock_post):
        client = PowerBIClient()
        client.execute_dax(DATASET, "EVALUATE A")
        client.execute_dax(DATASET, "EVALUATE B")

    urls = [llamada.args[0] for llamada in mock_post.call_args_list]
    assert len([u for u in urls if "login.microsoftonline.com" in u]) == 1
    assert len([u for u in urls if u.endswith("/executeQueries")]) == 2


def test_get_last_refresh(configurado) -> None:
    historial = [{"endTime": "2024-01-15T10:05:00Z", "status": "Completed"}]
    mock_get = MagicMock(return_value=_respuesta({"value": historial}))

    with (
        patch("app.scanner.powerbi_client.httpx.post", MagicMock(return_value=_token_respuesta())),
        patch("app.scanner.powerbi_client.httpx.get", mock_get),
    ):
        resultado = PowerBIClient().get_last_refresh(DATASET)

    assert resultado == datetime(2024, 1, 15, 10, 5, 0, tzinfo=timezone.utc)
    url, = mock_get.call_args.args
    assert url.endswith(f"/datasets/{DATASET}/refreshes")
    assert mock_get.call_args.kwargs["params"] == {"$top": "1"}


def test_get_last_refresh_sin_historial(configurado) -> None:
    mock_get = MagicMock(return_value=_respuesta({"value": []}))

    with (
        patch("app.scanner.powerbi_client.httpx.post", MagicMock(return_value=_token_respuesta())),
        patch("app.scanner.powerbi_client.httpx.get", mock_get),
    ):
        resultado = PowerBIClient().get_last_refresh(DATASET)

    assert resultado is None


def test_list_datasets(configurado) -> None:
    datasets = [{"id": DATASET, "name": "Dashboard Guardian"}]
    mock_get = MagicMock(return_value=_respuesta({"value": datasets}))

    with (
        patch("app.scanner.powerbi_client.httpx.post", MagicMock(return_value=_token_respuesta())),
        patch("app.scanner.powerbi_client.httpx.get", mock_get),
    ):
        resultado = PowerBIClient().list_datasets()

    assert resultado == datasets
    url, = mock_get.call_args.args
    assert url == f"{API_BASE}/groups/{WORKSPACE}/datasets"
    assert mock_get.call_args.kwargs["headers"]["Authorization"] == "Bearer tok-123"
