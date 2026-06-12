"""Tests de delivery/telegram.py con httpx mockeado (no llaman a la API real)."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config import settings
from app.delivery.telegram import CAPTION_MAX, MAX_INTENTOS, send_report, send_summary


def _respuesta_ok() -> MagicMock:
    respuesta = MagicMock()
    respuesta.raise_for_status.return_value = None
    respuesta.json.return_value = {"ok": True, "result": {"message_id": 1}}
    return respuesta


def test_send_summary_arma_el_request(monkeypatch) -> None:
    mock_post = MagicMock(return_value=_respuesta_ok())
    with patch("app.delivery.telegram.httpx.post", mock_post):
        resultado = send_summary("Todo en orden")

    assert resultado == {"message_id": 1}
    url, = mock_post.call_args.args
    assert url.endswith(f"/bot{settings.telegram_bot_token}/sendMessage")
    assert mock_post.call_args.kwargs["data"] == {
        "chat_id": settings.telegram_chat_id,
        "text": "Todo en orden",
    }


def test_send_report_adjunta_el_pdf(tmp_path) -> None:
    pdf = tmp_path / "informe.pdf"
    pdf.write_bytes(b"%PDF-1.7 prueba")
    mock_post = MagicMock(return_value=_respuesta_ok())

    with patch("app.delivery.telegram.httpx.post", mock_post):
        send_report("Resumen con hallazgos", pdf)

    url, = mock_post.call_args.args
    assert url.endswith("/sendDocument")
    assert mock_post.call_args.kwargs["data"]["caption"] == "Resumen con hallazgos"
    nombre, contenido, mime = mock_post.call_args.kwargs["files"]["document"]
    assert nombre == "informe.pdf"
    assert contenido == b"%PDF-1.7 prueba"
    assert mime == "application/pdf"


def test_send_report_trunca_el_caption(tmp_path) -> None:
    pdf = tmp_path / "informe.pdf"
    pdf.write_bytes(b"%PDF-1.7 prueba")
    mock_post = MagicMock(return_value=_respuesta_ok())

    with patch("app.delivery.telegram.httpx.post", mock_post):
        send_report("x" * 5000, pdf)

    caption = mock_post.call_args.kwargs["data"]["caption"]
    assert len(caption) == CAPTION_MAX
    assert caption.endswith("…")


def test_reintenta_con_backoff_y_recupera() -> None:
    mock_post = MagicMock(
        side_effect=[httpx.ConnectError("boom"), httpx.ConnectError("boom"), _respuesta_ok()]
    )
    mock_sleep = MagicMock()

    with (
        patch("app.delivery.telegram.httpx.post", mock_post),
        patch("app.delivery.telegram.time.sleep", mock_sleep),
    ):
        resultado = send_summary("hola")

    assert resultado == {"message_id": 1}
    assert mock_post.call_count == 3
    # backoff exponencial: 1s y luego 2s
    assert [llamada.args[0] for llamada in mock_sleep.call_args_list] == [1.0, 2.0]


def test_levanta_tras_agotar_los_intentos() -> None:
    mock_post = MagicMock(side_effect=httpx.ConnectError("boom"))

    with (
        patch("app.delivery.telegram.httpx.post", mock_post),
        patch("app.delivery.telegram.time.sleep", MagicMock()),
        pytest.raises(RuntimeError, match=f"tras {MAX_INTENTOS} intentos"),
    ):
        send_summary("hola")

    assert mock_post.call_count == MAX_INTENTOS
