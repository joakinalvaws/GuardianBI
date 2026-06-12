"""Notificaciones por Telegram con la Bot API directa (httpx).

Dos funciones públicas: send_summary(text) para el resumen ejecutivo y
send_report(text, pdf_path) para el resumen + PDF adjunto (sendDocument).
Ambas reintentan con backoff exponencial ante errores de red o HTTP.
"""

import time
from pathlib import Path

import httpx

from app.config import settings

API_BASE = "https://api.telegram.org"
MAX_INTENTOS = 3
BACKOFF_BASE_SEGUNDOS = 1.0
TIMEOUT_SEGUNDOS = 30.0
# La Bot API limita el caption a 1024 unidades UTF-16; 1000 deja margen
# para emojis y caracteres fuera del plano básico (cuentan doble).
CAPTION_MAX = 1000


def _post(metodo: str, data: dict, files: dict | None = None) -> dict:
    """POST a la Bot API con reintentos (backoff 1s, 2s, 4s…)."""
    url = f"{API_BASE}/bot{settings.telegram_bot_token}/{metodo}"
    ultimo_error: Exception | None = None
    for intento in range(MAX_INTENTOS):
        try:
            respuesta = httpx.post(url, data=data, files=files, timeout=TIMEOUT_SEGUNDOS)
            respuesta.raise_for_status()
            return respuesta.json()["result"]
        except httpx.HTTPError as exc:
            ultimo_error = exc
            if intento < MAX_INTENTOS - 1:
                time.sleep(BACKOFF_BASE_SEGUNDOS * 2**intento)
    raise RuntimeError(
        f"Telegram {metodo} falló tras {MAX_INTENTOS} intentos"
    ) from ultimo_error


def _truncar_caption(text: str) -> str:
    if len(text) <= CAPTION_MAX:
        return text
    return text[: CAPTION_MAX - 1] + "…"


def send_summary(text: str) -> dict:
    """Envía el resumen ejecutivo como mensaje de texto al chat configurado."""
    return _post("sendMessage", {"chat_id": settings.telegram_chat_id, "text": text})


def send_report(text: str, pdf_path: Path) -> dict:
    """Envía el PDF del informe con el resumen como caption (sendDocument)."""
    contenido = pdf_path.read_bytes()
    return _post(
        "sendDocument",
        {"chat_id": settings.telegram_chat_id, "caption": _truncar_caption(text)},
        files={"document": (pdf_path.name, contenido, "application/pdf")},
    )
