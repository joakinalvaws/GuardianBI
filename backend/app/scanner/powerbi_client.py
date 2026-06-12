"""Cliente de la Power BI REST API (ruta de producción, ver ADR-005).

En el MVP el scanner lee `dashboard_snapshots`; este cliente es el
reemplazo para auditar dashboards reales: autentica como service
principal (OAuth2 client credentials contra Entra ID) y consulta
datasets con DAX vía `executeQueries`. La guía de setup del tenant,
la app y el workspace está en docs/powerbi-production.md.
"""

import time

import httpx

from app.config import settings

TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
SCOPE = "https://analysis.windows.net/powerbi/api/.default"
API_BASE = "https://api.powerbi.com/v1.0/myorg"
TIMEOUT_SEGUNDOS = 30.0
# Renovar el token un poco antes de que expire (expires_in viene en segundos)
MARGEN_EXPIRACION_SEGUNDOS = 60


class PowerBINoConfigurado(RuntimeError):
    """Faltan las variables POWERBI_* en el entorno (ver docs/powerbi-production.md)."""


class PowerBIClient:
    """Service principal contra un workspace de Power BI."""

    def __init__(self) -> None:
        faltantes = [
            nombre
            for nombre, valor in {
                "POWERBI_TENANT_ID": settings.powerbi_tenant_id,
                "POWERBI_CLIENT_ID": settings.powerbi_client_id,
                "POWERBI_CLIENT_SECRET": settings.powerbi_client_secret,
                "POWERBI_WORKSPACE_ID": settings.powerbi_workspace_id,
            }.items()
            if not valor
        ]
        if faltantes:
            raise PowerBINoConfigurado(
                f"Faltan variables de entorno: {', '.join(faltantes)} "
                "(ver docs/powerbi-production.md)"
            )
        self._token: str | None = None
        self._token_expira_en: float = 0.0

    def _get_token(self) -> str:
        """Token de acceso por client credentials, cacheado hasta su expiración."""
        if self._token and time.monotonic() < self._token_expira_en:
            return self._token

        respuesta = httpx.post(
            TOKEN_URL.format(tenant=settings.powerbi_tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": settings.powerbi_client_id,
                "client_secret": settings.powerbi_client_secret,
                "scope": SCOPE,
            },
            timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
        self._token = cuerpo["access_token"]
        self._token_expira_en = (
            time.monotonic() + cuerpo["expires_in"] - MARGEN_EXPIRACION_SEGUNDOS
        )
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def list_datasets(self) -> list[dict]:
        """Datasets del workspace configurado (útil para verificar la conexión)."""
        respuesta = httpx.get(
            f"{API_BASE}/groups/{settings.powerbi_workspace_id}/datasets",
            headers=self._headers(),
            timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
        return respuesta.json()["value"]

    def execute_dax(self, dataset_id: str, consulta: str) -> list[dict]:
        """Ejecuta una consulta DAX contra un dataset y devuelve sus filas.

        Las claves de cada fila vienen como las nombra Power BI, p. ej.
        `[valor]` para `EVALUATE ROW("valor", [ventas_totales_mes])`.
        """
        respuesta = httpx.post(
            f"{API_BASE}/groups/{settings.powerbi_workspace_id}"
            f"/datasets/{dataset_id}/executeQueries",
            headers=self._headers(),
            json={"queries": [{"query": consulta}]},
            timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
        return respuesta.json()["results"][0]["tables"][0]["rows"]
