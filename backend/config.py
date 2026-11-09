import logging
import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _pairs(value: str) -> dict[str, str]:
    """"felix=Felix,sam=Sam" -> {"felix": "Felix", "sam": "Sam"}."""
    pairs = {}
    for item in _csv(value):
        key, sep, label = item.partition("=")
        if sep and key.strip() and label.strip():
            pairs[key.strip()] = label.strip()
    return pairs


AUTH_MODES = ("proxy", "basic", "none")
MIN_BASIC_PASSWORD = 12


def _normalize_auth_mode(mode: str) -> str:
    mode = (mode or "proxy").strip().lower()
    return "proxy" if mode == "authelia" else mode


def _async_url(url: str) -> str:
    """postgresql://... -> postgresql+asyncpg://..., sqlite://... -> sqlite+aiosqlite://..."""
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    return url


@dataclass
class Settings:
    environment: str = field(default_factory=lambda: _env("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    port: int = field(default_factory=lambda: int(_env("PORT", "8000")))
    database_url: str = field(
        default_factory=lambda: _async_url(_env("DATABASE_URL", "sqlite:///data/watchwhat.db"))
    )

    # Who may use the logged-in part (adding, editing, seen), app/auth.py:
    # "proxy" (alias "authelia"): a reverse proxy logs in and passes
    #   Remote-User plus the proxy secret.
    # "basic": the backend asks for HTTP Basic auth itself (BASIC_PASSWORD).
    # "none": everyone is logged in; only for a backend nobody else can reach.
    # The recommender and the library are public in every mode.
    auth_mode: str = field(default_factory=lambda: _env("AUTH_MODE", "proxy"))
    proxy_secret: str = field(default_factory=lambda: _env("PROXY_SECRET"))
    # The household: login names, comma-separated. Everyone in it has full
    # access, and "seen" is tracked for each of them.
    allowed_users: tuple[str, ...] = field(
        default_factory=lambda: _csv(_env("ALLOWED_USERS"))
    )
    basic_password: str = field(default_factory=lambda: _env("BASIC_PASSWORD"))
    # Optional names to show instead of login names: "felix=Felix,sam=Sam".
    display_names: dict[str, str] = field(
        default_factory=lambda: _pairs(_env("DISPLAY_NAMES"))
    )

    # TMDB API Read Access Token. Without it, movies are added by hand.
    tmdb_token: str = field(default_factory=lambda: _env("TMDB_TOKEN"))
    # Tagging. Without a key, drafts come without tags.
    anthropic_api_key: str = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "claude-haiku-5-5"))
    llm_effort: str = field(default_factory=lambda: _env("LLM_EFFORT", "low"))

    def __post_init__(self) -> None:
        self.auth_mode = _normalize_auth_mode(self.auth_mode)

    @property
    def debug(self) -> bool:
        return self.environment == "development"

    @property
    def household(self) -> tuple[str, ...]:
        if self.allowed_users:
            return self.allowed_users
        return ("local",) if self.auth_mode == "none" else ()

    def display_name(self, user: str) -> str:
        return self.display_names.get(user) or user[:1].upper() + user[1:]

    def validate(self) -> None:
        """Fail at startup instead of serving with a half-configured security setup."""
        self.auth_mode = _normalize_auth_mode(self.auth_mode)
        if self.auth_mode not in AUTH_MODES:
            raise RuntimeError(
                f"AUTH_MODE must be one of {', '.join(AUTH_MODES)} (or authelia), "
                f"got {self.auth_mode!r}"
            )
        if self.auth_mode == "proxy" and not self.debug:
            if not (self.proxy_secret and self.allowed_users):
                raise RuntimeError(
                    "AUTH_MODE=proxy: PROXY_SECRET and ALLOWED_USERS are required in production"
                )
        if self.auth_mode == "basic":
            if len(self.basic_password) < MIN_BASIC_PASSWORD:
                raise RuntimeError(
                    "AUTH_MODE=basic: BASIC_PASSWORD must have at least "
                    f"{MIN_BASIC_PASSWORD} characters"
                )
            if not self.allowed_users:
                raise RuntimeError("AUTH_MODE=basic: ALLOWED_USERS is required")
        if self.auth_mode == "none" and not self.debug:
            logging.getLogger(__name__).warning(
                "AUTH_MODE=none: anyone who reaches the backend can add, edit and delete"
            )
        if not self.debug and self.database_url.startswith("sqlite"):
            # Fine for one household; the file in the data dir is the backup.
            logging.getLogger(__name__).info("Using SQLite: %s", self.database_url)


settings = Settings()
