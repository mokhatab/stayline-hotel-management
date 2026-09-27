from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PostgresSettings:
    """Infrastructure-only database configuration."""

    dsn: str

    @classmethod
    def from_environment(cls) -> "PostgresSettings":
        dsn = os.environ.get("DATABASE_URL") or os.environ.get("HOTEL_DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "PostgreSQL requires DATABASE_URL or HOTEL_DATABASE_URL"
            )
        return cls(dsn=dsn)
