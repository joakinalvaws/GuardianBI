"""Verifica el bot de Telegram: identidad y envío real de mensaje.

Uso: python scripts/check_telegram.py
1. getMe — valida el token y muestra el nombre del bot.
2. sendMessage — envía un mensaje de prueba al TELEGRAM_CHAT_ID
   (debe llegarte al chat; si el bot nunca recibió un /start tuyo, falla).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from app.config import settings

API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


def main() -> int:
    # 1. Identidad del bot
    resp = httpx.get(f"{API}/getMe", timeout=15).json()
    if not resp.get("ok"):
        print(f"✗ FAIL getMe: {resp}")
        return 1
    bot = resp["result"]
    print(f"✓ Bot válido: @{bot['username']} ({bot['first_name']})")

    # 2. Mensaje real al chat
    resp = httpx.post(
        f"{API}/sendMessage",
        json={
            "chat_id": settings.telegram_chat_id,
            "text": "🛡️ Dashboard Guardian — conexión verificada. Fase 0 en marcha.",
        },
        timeout=15,
    ).json()
    if not resp.get("ok"):
        print(f"✗ FAIL sendMessage: {resp}")
        print("  Pista: abre el chat con el bot y mándale /start primero.")
        return 1
    print(f"✓ Mensaje enviado al chat {settings.telegram_chat_id} — revisa tu Telegram")

    print("\n✓ TELEGRAM OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
