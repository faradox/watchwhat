"""Logged in: the household's view, adding, editing, seen (plan section 6)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_user, login_user
from app.db import get_session, utcnow
from app.models import Movie, Seen
from app.schemas import (
    Flags,
    MeOut,
    MovieFields,
    Person,
    PrivateMovieOut,
    SeenIn,
    TagsOut,
    private_out,
)
from app.tagging import tag_movie

router = APIRouter(prefix="/private", tags=["private"])


def _person(settings, name: str) -> Person:
    return Person(name=name, display_name=settings.display_name(name))


@router.get("/login")
async def login(_user: str = Depends(login_user)) -> RedirectResponse:
    """Where the "Log in" link points. The proxy (or Basic auth) logs in first."""
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/me", response_model=MeOut)
async def me(request: Request, user: str = Depends(current_user)) -> MeOut:
    cfg = request.app.state.settings
    household = list(cfg.household) or [user]
    return MeOut(
        user=_person(cfg, user),
        household=[_person(cfg, name) for name in household],
        tmdb=request.app.state.tmdb is not None,
        tagging=request.app.state.tagger is not None,
    )


async def _movie(session: AsyncSession, movie_id: int) -> Movie:
    movie = await session.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such movie")
    return movie


@router.get("/movies", response_model=list[PrivateMovieOut])
async def list_movies(
    _user: str = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> list[PrivateMovieOut]:
    rows = await session.scalars(select(Movie).order_by(Movie.created_at.desc()))
    return [private_out(movie) for movie in rows]


@router.get("/movies/{movie_id}", response_model=PrivateMovieOut)
async def get_movie(
    movie_id: int,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PrivateMovieOut:
    return private_out(await _movie(session, movie_id))


async def _commit_or_conflict(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This movie is already on the list") from None


async def _check_tmdb_free(session: AsyncSession, tmdb_id: int | None, own_id: int | None) -> None:
    if tmdb_id is None:
        return
    other = await session.scalar(select(Movie.id).where(Movie.tmdb_id == tmdb_id))
    if other is not None and other != own_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This movie is already on the list")


@router.post("/movies", response_model=PrivateMovieOut, status_code=status.HTTP_201_CREATED)
async def create_movie(
    fields: MovieFields,
    user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PrivateMovieOut:
    await _check_tmdb_free(session, fields.tmdb_id, None)
    now = utcnow()
    movie = Movie(**fields.model_dump(), added_by=user, created_at=now, updated_at=now, seen=[])
    session.add(movie)
    await _commit_or_conflict(session)
    return private_out(movie)


@router.put("/movies/{movie_id}", response_model=PrivateMovieOut)
async def update_movie(
    movie_id: int,
    fields: MovieFields,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PrivateMovieOut:
    movie = await _movie(session, movie_id)
    await _check_tmdb_free(session, fields.tmdb_id, movie.id)
    for key, value in fields.model_dump().items():
        setattr(movie, key, value)
    movie.updated_at = utcnow()
    await _commit_or_conflict(session)
    return private_out(movie)


@router.patch("/movies/{movie_id}", response_model=PrivateMovieOut)
async def update_flags(
    movie_id: int,
    flags: Flags,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PrivateMovieOut:
    movie = await _movie(session, movie_id)
    for key, value in flags.model_dump(exclude_none=True).items():
        setattr(movie, key, value)
    movie.updated_at = utcnow()
    await session.commit()
    return private_out(movie)


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: int,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    movie = await _movie(session, movie_id)
    await session.delete(movie)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/movies/{movie_id}/seen", response_model=PrivateMovieOut)
async def set_seen(
    movie_id: int,
    body: SeenIn,
    request: Request,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PrivateMovieOut:
    """Who has seen it: one person, both ("users": everyone), or nobody."""
    household = set(request.app.state.settings.household)
    movie = await _movie(session, movie_id)
    have = {s.user_name for s in movie.seen}
    # Marks of people who left the household come back from the page; drop them.
    unknown = set(body.users) - household - have
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Not in the household: {', '.join(sorted(unknown))}"
        )
    wanted = set(body.users) & household
    for entry in [s for s in movie.seen if s.user_name not in wanted]:
        movie.seen.remove(entry)
    now = utcnow()
    for name in sorted(wanted - have):
        movie.seen.append(Seen(user_name=name, seen_at=now))
    await session.commit()
    return private_out(movie)


@router.post("/movies/{movie_id}/retag", response_model=TagsOut)
async def retag(
    movie_id: int,
    request: Request,
    _user: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> TagsOut:
    """New suggestions for a saved movie; nothing is stored."""
    movie = await _movie(session, movie_id)
    fields = MovieFields.model_validate(movie, from_attributes=True)
    tags = await tag_movie(request.app.state.tagger, fields, raise_errors=True)
    return TagsOut(**{name: getattr(tags, name) for name in TagsOut.model_fields})
