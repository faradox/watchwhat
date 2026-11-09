import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api import add, private, public
from app.db import make_sessionmaker
from config import Settings, settings

log = logging.getLogger(__name__)


def default_tmdb(cfg: Settings):
    if not cfg.tmdb_token:
        return None
    from app.tmdb import TMDB

    return TMDB(cfg.tmdb_token)


def default_tagger(cfg: Settings):
    if not cfg.anthropic_api_key:
        return None
    from app.tagger import Tagger

    return Tagger(cfg.anthropic_api_key, cfg.llm_model, cfg.llm_effort)


def create_app(
    cfg: Settings = settings, tmdb_factory=default_tmdb, tagger_factory=default_tagger
) -> FastAPI:
    cfg.validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = cfg
        app.state.sessionmaker = make_sessionmaker(cfg.database_url)
        app.state.tmdb = tmdb_factory(cfg)
        app.state.tagger = tagger_factory(cfg)
        if app.state.tmdb is None:
            log.warning("No TMDB_TOKEN: movies can only be added by hand")
        if app.state.tagger is None:
            log.warning("No ANTHROPIC_API_KEY: drafts come without tags")
        try:
            yield
        finally:
            for client in (app.state.tmdb, app.state.tagger):
                if client is not None:
                    await client.close()
            await app.state.sessionmaker.kw["bind"].dispose()

    app = FastAPI(
        title="watchwhat",
        docs_url="/api/docs" if cfg.debug else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if cfg.debug else None,
        lifespan=lifespan,
    )
    for module in (public, private, add):
        app.include_router(module.router, prefix="/api")
    return app


logging.basicConfig(level=settings.log_level)

if __name__ == "__main__":
    uvicorn.run(
        "main:create_app",
        factory=True,
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        reload_excludes=["data"] if settings.debug else None,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
