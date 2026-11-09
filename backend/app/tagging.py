"""Glue between saved/draft movies and the tagger."""

import logging

from fastapi import HTTPException, status

from app.schemas import MovieFields
from app.tagger import Tags, TaggerError

log = logging.getLogger(__name__)

# What the model sees about a movie: facts only, never tags or flags.
FACT_FIELDS = (
    "title",
    "original_title",
    "original_language",
    "year",
    "runtime_min",
    "genres",
    "keywords",
    "director",
    "cast",
    "overview",
)

ERROR_TEXT = {
    "off": "Tagging is off on this server (no Anthropic API key).",
    "auth": "The Anthropic API key was rejected.",
    "rate_limited": "The tagging service is busy; try again in a minute.",
    "timeout": "The tagging service took too long; try again.",
    "connection": "The tagging service could not be reached.",
}


def tag_error_text(kind: str) -> str:
    return ERROR_TEXT.get(kind, f"Tagging failed ({kind}).")


async def tag_movie(tagger, fields: MovieFields, raise_errors: bool = False) -> Tags:
    """Suggested tags, or empty tags with the reason in `.error` (raise_errors: 502)."""
    if tagger is None:
        if raise_errors:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, tag_error_text("off"))
        return _failed("off")
    facts = {name: getattr(fields, name) for name in FACT_FIELDS}
    try:
        return await tagger.tag(facts)
    except TaggerError as exc:
        log.warning("tagging failed: %s", exc.kind)
        if raise_errors:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, tag_error_text(exc.kind)) from exc
        return _failed(exc.kind)


def _failed(kind: str) -> Tags:
    return Tags(error=kind)
