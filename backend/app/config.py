"""Configuración central de Dashboard Guardian.

Única puerta de entrada a las variables de entorno: el resto del código
importa `settings` desde aquí y nunca usa `os.environ` directo.
Lee `backend/.env` sin importar desde qué directorio se ejecute.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ — el .env vive junto a requirements.txt, no junto a app/
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Variables de entorno de la aplicación (ver backend/.env.example)."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- OpenAI ---
    openai_api_key: str
    openai_model: str = "gpt-5.4-mini"

    # --- Supabase ---
    supabase_url: str
    supabase_publishable_key: str = ""  # lectura (frontend, Fase 5)
    supabase_secret_key: str            # escritura (service_role; seed/inject/backend)

    # --- Telegram ---
    telegram_bot_token: str
    telegram_chat_id: str

    # --- Power BI (vacío en MVP, Fase 6) ---
    powerbi_tenant_id: str = ""
    powerbi_client_id: str = ""
    powerbi_client_secret: str = ""
    powerbi_workspace_id: str = ""

    # --- AWS SES (opcional, Fase 2) ---
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    ses_from_email: str = ""

    # --- App ---
    environment: str = "development"
    audit_schedule_cron: str = "0 7 * * *"
    stale_data_threshold_hours: int = 24
    metric_tolerance_pct: float = 1.0


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia única de Settings (cacheada)."""
    return Settings()


settings = get_settings()
