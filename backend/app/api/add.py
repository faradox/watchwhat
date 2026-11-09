"""Logged in: find a movie on TMDB and get a tagged draft (plan section 4).

Nothing here writes to the database; saving a draft is POST /private/movies.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user
from app.db import get_session
from app.models import Movie
from app.schemas import CandidateOut, Draft, DraftIn, MovieFields
from app.tagging import tag_error_text, tag_movie
from app.tmdb import TMDBError
from app import vocab

router = APIRouter(prefix="/private", tags=["add"])

TMDB_ERROR_TEXT = {
    "auth": "TMDB rejected the token.",
    "not_found": "TMDB does not know this movie.",
    "rate_limited": "TMDB is busy; try again in a few seconds.",
    "timeout": "TMDB took too long to answer; try again.",
    "connection": "TMDB could not be reached.",
}


def _tmdb(request: Request):
    tmdb = request.app.state.tmdb
    if tmdb is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "TMDB is not configured on this server; add the movie by hand.",
        )
    return tmdb


def _tmdb_failed(exc: TMDBError) -> HTTPException:
    code = status.HTTP_404_NOT_FOUND if exc.kind == "not_found" else status.HTTP_502_BAD_GATEWAY
    return HTTPException(code, TMDB_ERROR_TEXT.get(exc.kind, f"TMDB failed ({exc.kind})."))


async def _on_list(session: AsyncSession, tmdb_ids: list[int]) -> dict[int, int]:
    if not tmdb_ids:
        return {}
    rows = await session.execute(
        select(Movie.tmdb_id, Movie.id).where(Movie.tmdb_id.in_(tmdb_ids))
    )
    return {tmdb_id: movie_id for tmdb_id, movie_id in rows}


@router.get("/tmdb/search", response_model=list[CandidateOut])
async def search(
    request: Request,
    q: str = Query(min_length=1, max_length=200),
    year: int | None = Query(default=None, ge=1870, le=2100),
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CandidateOut]:
    tmdb = _tmdb(request)
    try:
        candidates = await tmdb.search(q.strip(), year)
    except TMDBError as exc:
        raise _tmdb_failed(exc) from exc
    known = await _on_list(session, [c.tmdb_id for c in candidates])
    return [CandidateOut(**c.__dict__, on_list=known.get(c.tmdb_id)) for c in candidates]


@router.post("/drafts", response_model=Draft)
async def make_draft(
    body: DraftIn,
    request: Request,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Draft:
    """The facts (TMDB, or what was typed in) plus suggested tags. Not stored."""
    already = None
    if body.tmdb_id is not None:
        try:
            facts = await _tmdb(request).facts(body.tmdb_id)
        except TMDBError as exc:
            raise _tmdb_failed(exc) from exc
        already = (await _on_list(session, [facts.tmdb_id])).get(facts.tmdb_id)
        known_genres = [g for g in facts.genres if g in vocab.GENRES]
        fields = MovieFields(**{**facts.__dict__, "genres": known_genres}, verified=True)
    else:
        if not (body.title or "").strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A title is needed")
        fields = MovieFields(
            title=body.title,
            year=body.year,
            runtime_min=body.runtime_min,
            overview=body.overview,
            original_language=body.original_language,
            verified=False,
        )
    draft = Draft(**fields.model_dump(), already_on_list=already)
    if already is not None:
        # Nothing to save, so nothing to pay for.
        return draft
    tags = await tag_movie(request.app.state.tagger, fields)
    if tags.error:
        # No blurb: the card shows the overview instead.
        draft.tag_error = tag_error_text(tags.error)
    else:
        draft.moods = tags.moods
        draft.attention = tags.attention
        draft.violence = tags.violence
        draft.scariness = tags.scariness
        draft.heaviness = tags.heaviness
        draft.blurb = tags.blurb
    return draft
