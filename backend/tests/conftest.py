from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from config import Settings
from main import create_app
from tests.fakes import FakeTagger, FakeTMDBServer

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROXY_SECRET = "test-proxy-secret"


def migrate(database_url: str) -> None:
    """The real migrations, so tests fail when models and migrations drift apart."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = database_url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def make_settings(tmp_path, **overrides) -> Settings:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'watchwhat.db'}"
    migrate(db_url)
    values = dict(
        environment="development",
        database_url=db_url,
        auth_mode="proxy",
        proxy_secret=PROXY_SECRET,
        allowed_users=("felix", "sam"),
        basic_password="",
        display_names={"sam": "Sam"},
        # Nothing from the environment (tests may run where real keys are set).
        tmdb_token="",
        anthropic_api_key="",
        llm_model="claude-haiku-5-5",
        llm_effort="low",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture(autouse=True)
def no_real_clients(monkeypatch):
    """Creating a real Anthropic client fails the test: the API costs money."""
    from app import tagger

    def refuse(*_args, **_kwargs):
        raise AssertionError("a test tried to create a real Anthropic client")

    monkeypatch.setattr(tagger.Tagger, "__init__", refuse)


def as_user(name: str = "felix") -> dict:
    """Headers nginx sends after a successful Authelia check."""
    return {"Remote-User": name, "X-Proxy-Secret": PROXY_SECRET}


@pytest.fixture
def settings(tmp_path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def tmdb_server() -> FakeTMDBServer:
    return FakeTMDBServer()


@pytest.fixture
def tagger() -> FakeTagger:
    return FakeTagger()


def make_client(settings, tmdb_server=None, tagger=None) -> TestClient:
    return TestClient(
        create_app(
            settings,
            tmdb_factory=lambda _cfg: tmdb_server.client() if tmdb_server else None,
            tagger_factory=lambda _cfg: tagger,
        )
    )


@pytest.fixture
def client(settings, tmdb_server, tagger):
    with make_client(settings, tmdb_server, tagger) as c:
        yield c


def movie_body(**overrides) -> dict:
    body = {
        "title": "Paddington 2",
        "year": 2017,
        "runtime_min": 104,
        "genres": ["Comedy", "Family"],
        "moods": ["feel-good", "funny"],
        "attention": "brain-off",
        "violence": 0,
        "scariness": 0,
        "heaviness": 0,
        "blurb": "A bear, a pop-up book, and a prison that learns to make marmalade.",
    }
    body.update(overrides)
    return body


@pytest.fixture
def add_movie(client):
    def add(**overrides) -> dict:
        res = client.post("/api/private/movies", json=movie_body(**overrides), headers=as_user())
        assert res.status_code == 201, res.text
        return res.json()

    return add
