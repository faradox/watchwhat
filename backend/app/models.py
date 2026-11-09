from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, UTCDateTime


class Movie(Base):
    __tablename__ = "movie"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Null for movies entered by hand (TMDB does not know them).
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    imdb_id: Mapped[str | None] = mapped_column(String(16))

    # English title (TMDB "title") and the title in the original language.
    title: Mapped[str] = mapped_column(String(300))
    original_title: Mapped[str | None] = mapped_column(String(300))
    original_language: Mapped[str | None] = mapped_column(String(8))
    year: Mapped[int | None] = mapped_column(Integer)
    runtime_min: Mapped[int | None] = mapped_column(Integer)
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    director: Mapped[str | None] = mapped_column(String(200))
    cast: Mapped[list[str]] = mapped_column(JSON, default=list)
    overview: Mapped[str | None] = mapped_column(Text)
    poster_path: Mapped[str | None] = mapped_column(String(200))
    trailer_youtube_key: Mapped[str | None] = mapped_column(String(32))
    vote_average: Mapped[float | None] = mapped_column(Float)

    # Tags (app/vocab.py). The LLM suggests them, people may change them.
    blurb: Mapped[str | None] = mapped_column(Text)
    moods: Mapped[list[str]] = mapped_column(JSON, default=list)
    attention: Mapped[str | None] = mapped_column(String(16))
    violence: Mapped[int | None] = mapped_column(Integer)
    scariness: Mapped[int | None] = mapped_column(Integer)
    heaviness: Mapped[int | None] = mapped_column(Integer)

    # "We both really want to see this": comes up more often.
    priority: Mapped[bool] = mapped_column(Boolean, default=False)
    # Kept in the library but never recommended.
    never_suggest: Mapped[bool] = mapped_column(Boolean, default=False)
    # False for movies entered by hand: nothing was checked against TMDB.
    verified: Mapped[bool] = mapped_column(Boolean, default=True)

    added_by: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)

    seen: Mapped[list["Seen"]] = relationship(
        back_populates="movie", cascade="all, delete-orphan", lazy="selectin"
    )


class Seen(Base):
    """One person has seen one movie."""

    __tablename__ = "seen"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movie.id", ondelete="CASCADE"), primary_key=True
    )
    user_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(UTCDateTime)

    movie: Mapped[Movie] = relationship(back_populates="seen")
