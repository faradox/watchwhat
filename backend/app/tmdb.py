"""TMDB API client (plan section 2): search, and the facts for one movie.

The token never leaves this module and is never logged. Tests pass an
httpx transport with canned answers (tests/fakes.py).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

BASE_URL = "https://api.themoviedb.org/3"
TIMEOUT_SECONDS = 15.0
MAX_CAST = 6
MAX_KEYWORDS = 20

log = logging.getLogger(__name__)


class TMDBError(Exception):
    """A failed request. `kind` is a short code, safe to log and show."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


@dataclass
class Candidate:
    tmdb_id: int
    title: str
    original_title: str | None
    original_language: str | None
    year: int | None
    overview: str | None
    poster_path: str | None


@dataclass
class Facts:
    tmdb_id: int
    imdb_id: str | None
    title: str
    original_title: str | None
    original_language: str | None
    year: int | None
    runtime_min: int | None
    genres: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    director: str | None = None
    cast: list[str] = field(default_factory=list)
    overview: str | None = None
    poster_path: str | None = None
    trailer_youtube_key: str | None = None
    vote_average: float | None = None


def _year(date: str | None) -> int | None:
    if date and len(date) >= 4 and date[:4].isdigit():
        return int(date[:4])
    return None


def _text(value) -> str | None:
    value = (value or "").strip() if isinstance(value, str) else None
    return value or None


def pick_trailer(videos: list[dict]) -> str | None:
    """The best YouTube trailer key: official trailers first, then any trailer,
    then teasers. Ties keep TMDB's order."""
    def rank(video: dict) -> tuple[int, int]:
        kind = {"Trailer": 0, "Teaser": 1}.get(video.get("type"), 9)
        return (kind, 0 if video.get("official") else 1)

    youtube = [v for v in videos if v.get("site") == "YouTube" and v.get("key")]
    youtube = [v for v in youtube if rank(v)[0] < 9]
    if not youtube:
        return None
    return min(youtube, key=rank)["key"]


def parse_candidate(item: dict) -> Candidate:
    return Candidate(
        tmdb_id=int(item["id"]),
        title=_text(item.get("title")) or _text(item.get("original_title")) or "?",
        original_title=_text(item.get("original_title")),
        original_language=_text(item.get("original_language")),
        year=_year(item.get("release_date")),
        overview=_text(item.get("overview")),
        poster_path=_text(item.get("poster_path")),
    )


def parse_facts(data: dict) -> Facts:
    credits = data.get("credits") or {}
    directors = [c["name"] for c in credits.get("crew") or [] if c.get("job") == "Director"]
    cast = sorted(credits.get("cast") or [], key=lambda c: c.get("order", 999))
    keywords = (data.get("keywords") or {}).get("keywords") or []
    videos = (data.get("videos") or {}).get("results") or []
    imdb_id = _text(data.get("imdb_id")) or _text(
        (data.get("external_ids") or {}).get("imdb_id")
    )
    vote = data.get("vote_average")
    return Facts(
        tmdb_id=int(data["id"]),
        imdb_id=imdb_id,
        title=_text(data.get("title")) or _text(data.get("original_title")) or "?",
        original_title=_text(data.get("original_title")),
        original_language=_text(data.get("original_language")),
        year=_year(data.get("release_date")),
        runtime_min=data.get("runtime") or None,
        genres=[g["name"] for g in data.get("genres") or [] if g.get("name")],
        keywords=[k["name"] for k in keywords[:MAX_KEYWORDS] if k.get("name")],
        director=", ".join(directors[:2]) or None,
        cast=[c["name"] for c in cast[:MAX_CAST] if c.get("name")],
        overview=_text(data.get("overview")),
        poster_path=_text(data.get("poster_path")),
        trailer_youtube_key=pick_trailer(videos),
        vote_average=float(vote) if vote else None,
    )


class TMDB:
    def __init__(self, token: str, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict) -> dict:
        try:
            res = await self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise TMDBError("timeout") from exc
        except httpx.HTTPError as exc:
            raise TMDBError("connection") from exc
        if res.status_code == 401:
            raise TMDBError("auth")
        if res.status_code == 404:
            raise TMDBError("not_found")
        if res.status_code == 429:
            raise TMDBError("rate_limited")
        if res.status_code >= 400:
            raise TMDBError(f"http_{res.status_code}")
        try:
            return res.json()
        except ValueError as exc:
            raise TMDBError("bad_response") from exc

    async def search(self, query: str, year: int | None = None) -> list[Candidate]:
        params = {"query": query, "include_adult": "false", "language": "en-US"}
        if year:
            params["year"] = str(year)
        data = await self._get("/search/movie", params)
        results = [parse_candidate(item) for item in data.get("results") or [] if "id" in item]
        if year and not results:
            # A wrong year guess should not hide the movie.
            return await self.search(query)
        return results[:12]

    async def facts(self, tmdb_id: int) -> Facts:
        data = await self._get(
            f"/movie/{tmdb_id}",
            {
                "language": "en-US",
                "append_to_response": "videos,keywords,external_ids,credits",
                "include_video_language": "en,null",
            },
        )
        facts = parse_facts(data)
        if facts.trailer_youtube_key is None and facts.original_language not in (None, "en"):
            # Many non-English films only have a trailer in their own language.
            try:
                videos = await self._get(
                    f"/movie/{tmdb_id}/videos",
                    {"include_video_language": f"{facts.original_language},null"},
                )
                facts.trailer_youtube_key = pick_trailer(videos.get("results") or [])
            except TMDBError as exc:
                log.info("TMDB videos for %s failed: %s", tmdb_id, exc.kind)
        return facts
