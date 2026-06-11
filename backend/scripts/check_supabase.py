"""Verifica la conexión a Supabase con la secret key (service_role).

Uso: python scripts/check_supabase.py
Valida que la URL y la key sean correctas pidiendo el esquema REST
(funciona aunque todavía no existan tablas) y que supabase-py cree el cliente.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from supabase import create_client

from app.config import settings


def main() -> int:
    print(f"→ Supabase URL: {settings.supabase_url}")

    # 1. Validar URL + key contra la API REST (200 = key válida, 401 = inválida)
    resp = httpx.get(
        f"{settings.supabase_url}/rest/v1/",
        headers={
            "apikey": settings.supabase_secret_key,
            "Authorization": f"Bearer {settings.supabase_secret_key}",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"✗ FAIL: la API REST respondió {resp.status_code}: {resp.text[:200]}")
        return 1
    print("✓ API REST responde 200 con la secret key")

    # 2. Validar que supabase-py crea el cliente sin errores
    create_client(settings.supabase_url, settings.supabase_secret_key)
    print("✓ supabase-py creó el cliente")

    print("\n✓ SUPABASE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
