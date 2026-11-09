"""Public, read-only: health, vocabularies, and the list without private fields."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import vocab
from app.db import get_session
from app.models import Movie
from app.schemas import MovieOut, public_out

router = APIRouter(tags=["public"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/vocab")
async def get_vocab():
    return vocab.as_json()


@router.get("/movies", response_model=list[MovieOut])
async def list_movies(session: AsyncSession = Depends(get_session)) -> list[MovieOut]:
    rows = await session.scalars(
        select(Movie).where(Movie.never_suggest.is_(False)).order_by(Movie.created_at.desc())
    )
    return [public_out(movie) for movie in rows]


@router.get("/movies/{movie_id}", response_model=MovieOut)
async def get_movie(movie_id: int, session: AsyncSession = Depends(get_session)) -> MovieOut:
    movie = await session.get(Movie, movie_id)
    if movie is None or movie.never_suggest:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such movie")
    return public_out(movie)
