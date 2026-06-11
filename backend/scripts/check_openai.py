"""Verifica la API key de OpenAI y que el modelo del plan exista.

Uso: python scripts/check_openai.py
1. Recupera el modelo configurado (settings.openai_model); si no existe,
   lista los modelos disponibles para elegir una alternativa.
2. Hace una llamada mínima de chat para confirmar acceso real.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import NotFoundError, OpenAI

from app.config import settings


def main() -> int:
    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.openai_model
    print(f"→ Verificando modelo: {model}")

    # 1. ¿Existe el modelo?
    try:
        client.models.retrieve(model)
        print(f"✓ El modelo {model} existe y la key tiene acceso")
    except NotFoundError:
        print(f"✗ FAIL: el modelo {model} NO existe o la key no tiene acceso.")
        print("\nModelos disponibles (filtrados a gpt/o):")
        for m in sorted(client.models.list(), key=lambda m: m.id):
            if m.id.startswith(("gpt", "o")):
                print(f"  - {m.id}")
        return 1

    # 2. Llamada mínima real
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Responde únicamente: OK"}],
    )
    answer = (resp.choices[0].message.content or "").strip()
    print(f"✓ Respuesta del modelo: {answer!r}")

    print("\n✓ OPENAI OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
