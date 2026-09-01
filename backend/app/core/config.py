"""Central place for every environment-driven setting.

Loading backend/.env here means no other module needs to know dotenv exists.
Mirrors src/config.js: the same variables, the same defaults, the same
fail-fast behaviour when something required is missing.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
ENV_FILE = BACKEND_DIR / ".env"

# Load into os.environ as well, so alembic and one-off scripts see the values.
load_dotenv(ENV_FILE)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    node_env: str = "development"
    port: int = 5000
    database_url: str = ""
    jwt_secret: str = ""
    jwt_expires_in: str = "30d"
    # Comma-separated list, or "*" to allow any origin (fine for local use —
    # the API is token-protected and runs on the owner's own machine).
    cors_origin: str = "*"
    # Base64 signatures and product photos make request bodies large.
    json_body_limit: str = "8mb"

    @property
    def is_production(self) -> bool:
        return self.node_env == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_origin.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origin.split(",") if origin.strip()]

    @property
    def json_body_limit_bytes(self) -> int:
        return _parse_size(self.json_body_limit)

    @property
    def jwt_expires_in_seconds(self) -> int:
        return _parse_duration(self.jwt_expires_in)


def _parse_size(value: str) -> int:
    """'8mb' -> 8388608. Accepts a bare number of bytes too."""
    raw = str(value).strip().lower()
    units = {"kb": 1024, "mb": 1024**2, "gb": 1024**3, "b": 1}
    for suffix, factor in units.items():
        if raw.endswith(suffix):
            number = raw[: -len(suffix)].strip()
            try:
                return int(float(number) * factor)
            except ValueError:
                break
    try:
        return int(float(raw))
    except ValueError:
        return 8 * 1024**2


def _parse_duration(value: str) -> int:
    """'30d' -> 2592000 seconds. Same vocabulary as jsonwebtoken's expiresIn."""
    raw = str(value).strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
    if raw and raw[-1] in units:
        try:
            return int(float(raw[:-1]) * units[raw[-1]])
        except ValueError:
            pass
    try:
        return int(float(raw))
    except ValueError:
        return 30 * 86400


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    missing = [
        name
        for name, value in (("DATABASE_URL", settings.database_url), ("JWT_SECRET", settings.jwt_secret))
        if not value
    ]
    if missing:
        print(
            f"Missing required environment variable(s): {', '.join(missing)}\n"
            "Copy backend/.env.example to backend/.env and fill it in.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if settings.is_production and len(settings.jwt_secret) < 32:
        print("JWT_SECRET must be at least 32 characters in production.", file=sys.stderr)
        raise SystemExit(1)

    return settings


settings = get_settings()
