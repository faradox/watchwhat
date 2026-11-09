"""API shapes. Public answers never contain seen status or who added what."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app import vocab
from app.models import Movie

_YOUTUBE_KEY = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
_YOUTUBE_URL = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,20})"
)
_IMDB = re.compile(r"(tt\d{5,10})")


def youtube_key(value: str | None) -> str | None:
    """A YouTube video id from an id or any common YouTube URL."""
    value = (value or "").strip()
    if not value:
        return None
    if _YOUTUBE_KEY.match(value):
        return value
    match = _YOUTUBE_URL.search(value)
    if not match:
        raise ValueError("not a YouTube link or video id")
    return match.group(1)


def imdb_id(value: str | None) -> str | None:
    """tt1234567 from an id or an IMDb URL."""
    value = (value or "").strip()
    if not value:
        return None
    match = _IMDB.search(value)
    if not match:
        raise ValueError("not an IMDb link or id (tt...)")
    return match.group(1)


def _blank_to_none(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class MovieFields(BaseModel):
    """Everything about a movie that can be saved or edited."""

    tmdb_id: int | None = None
    imdb_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    original_title: str | None = Field(default=None, max_length=300)
    original_language: str | None = Field(default=None, max_length=8)
    year: int | None = Field(default=None, ge=1870, le=2100)
    runtime_min: int | None = Field(default=None, ge=1, le=1500)
    genres: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list, max_length=40)
    director: str | None = Field(default=None, max_length=200)
    cast: list[str] = Field(default_factory=list, max_length=20)
    overview: str | None = Field(default=None, max_length=5000)
    poster_path: str | None = Field(default=None, max_length=200, pattern=r"^/[\w.-]+$")
    trailer_youtube_key: str | None = None
    vote_average: float | None = Field(default=None, ge=0, le=10)

    blurb: str | None = Field(default=None, max_length=600)
    moods: list[str] = Field(default_factory=list)
    attention: str | None = None
    violence: int | None = Field(default=None, ge=0, le=3)
    scariness: int | None = Field(default=None, ge=0, le=3)
    heaviness: int | None = Field(default=None, ge=0, le=3)

    priority: bool = False
    never_suggest: bool = False
    verified: bool = True

    _strip = field_validator(
        "title", "original_title", "original_language", "director", "overview", "blurb",
        "poster_path", mode="before",
    )(_blank_to_none)

    @field_validator("trailer_youtube_key", mode="before")
    @classmethod
    def _youtube(cls, value):
        return youtube_key(value)

    @field_validator("imdb_id", mode="before")
    @classmethod
    def _imdb(cls, value):
        return imdb_id(value)

    @field_validator("genres")
    @classmethod
    def _genres(cls, value: list[str]) -> list[str]:
        unknown = [g for g in value if g not in vocab.GENRES]
        if unknown:
            raise ValueError(f"unknown genres: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("moods")
    @classmethod
    def _moods(cls, value: list[str]) -> list[str]:
        unknown = [m for m in value if m not in vocab.MOODS]
        if unknown:
            raise ValueError(f"unknown moods: {', '.join(unknown)}")
        value = list(dict.fromkeys(value))
        if len(value) > vocab.MAX_MOODS:
            raise ValueError(f"at most {vocab.MAX_MOODS} moods")
        return value

    @field_validator("attention")
    @classmethod
    def _attention(cls, value: str | None) -> str | None:
        if value is not None and value not in vocab.ATTENTION:
            raise ValueError(f"unknown attention {value!r}")
        return value

    @field_validator("keywords", "cast")
    @classmethod
    def _names(cls, value: list[str]) -> list[str]:
        return [v.strip()[:200] for v in value if isinstance(v, str) and v.strip()]


class MovieOut(BaseModel):
    """What everyone may see."""

    id: int
    tmdb_id: int | None
    imdb_id: str | None
    title: str
    original_title: str | None
    original_language: str | None
    year: int | None
    runtime_min: int | None
    genres: list[str]
    keywords: list[str]
    director: str | None
    cast: list[str]
    overview: str | None
    poster_path: str | None
    trailer_youtube_key: str | None
    vote_average: float | None
    blurb: str | None
    moods: list[str]
    attention: str | None
    violence: int | None
    scariness: int | None
    heaviness: int | None
    priority: bool
    verified: bool
    created_at: datetime


class PrivateMovieOut(MovieOut):
    never_suggest: bool
    added_by: str | None
    seen_by: list[str]


_PUBLIC_FIELDS = tuple(MovieOut.model_fields)


def public_out(movie: Movie) -> MovieOut:
    return MovieOut(**{name: getattr(movie, name) for name in _PUBLIC_FIELDS})


def private_out(movie: Movie) -> PrivateMovieOut:
    return PrivateMovieOut(
        **{name: getattr(movie, name) for name in _PUBLIC_FIELDS},
        never_suggest=movie.never_suggest,
        added_by=movie.added_by,
        seen_by=sorted(s.user_name for s in movie.seen),
    )


class Flags(BaseModel):
    priority: bool | None = None
    never_suggest: bool | None = None


class SeenIn(BaseModel):
    # Everyone in the household who has seen it; [] clears.
    users: list[str]


class DraftIn(BaseModel):
    """Either a TMDB movie, or a movie entered by hand."""

    tmdb_id: int | None = None
    title: str | None = Field(default=None, max_length=300)
    year: int | None = Field(default=None, ge=1870, le=2100)
    runtime_min: int | None = Field(default=None, ge=1, le=1500)
    overview: str | None = Field(default=None, max_length=5000)
    original_language: str | None = Field(default=None, max_length=8)


class Draft(MovieFields):
    # Why there are no tags, if there are none: "off" (no API key) or an error code.
    tag_error: str | None = None
    # The id of the movie if this TMDB movie is already on the list.
    already_on_list: int | None = None


class TagsOut(BaseModel):
    blurb: str | None
    moods: list[str]
    attention: str | None
    violence: int | None
    scariness: int | None
    heaviness: int | None


class CandidateOut(BaseModel):
    tmdb_id: int
    title: str
    original_title: str | None
    original_language: str | None
    year: int | None
    overview: str | None
    poster_path: str | None
    on_list: int | None


class Person(BaseModel):
    name: str
    display_name: str


class MeOut(BaseModel):
    user: Person
    household: list[Person]
    # Which helpers are configured on this server.
    tmdb: bool
    tagging: bool
