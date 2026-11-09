"""Stand-ins for TMDB and the tagger. No test ever reaches the network."""

import json

import httpx

from app.tagger import Tags, TaggerError
from app.tmdb import TMDB

ALIEN = {
    "id": 348,
    "imdb_id": "tt0078748",
    "title": "Alien",
    "original_title": "Alien",
    "original_language": "en",
    "release_date": "1979-05-25",
    "runtime": 117,
    "genres": [{"id": 27, "name": "Horror"}, {"id": 878, "name": "Science Fiction"}],
    "overview": "During its return to the earth, commercial spaceship Nostromo intercepts a distress signal.",
    "poster_path": "/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg",
    "vote_average": 8.2,
    "credits": {
        "cast": [
            {"name": "Tom Skerritt", "order": 1},
            {"name": "Sigourney Weaver", "order": 0},
        ],
        "crew": [{"name": "Ridley Scott", "job": "Director"}, {"name": "X", "job": "Editor"}],
    },
    "keywords": {"keywords": [{"name": "space"}, {"name": "android"}]},
    "videos": {
        "results": [
            {"site": "YouTube", "key": "teaser00001", "type": "Teaser", "official": True},
            {"site": "YouTube", "key": "fanmade0001", "type": "Trailer", "official": False},
            {"site": "YouTube", "key": "LjLamj-b0I8", "type": "Trailer", "official": True},
            {"site": "Vimeo", "key": "123", "type": "Trailer", "official": True},
        ]
    },
}

SEVEN_SAMURAI = {
    "id": 346,
    "imdb_id": "tt0047478",
    "title": "Seven Samurai",
    "original_title": "七人の侍",
    "original_language": "ja",
    "release_date": "1954-04-26",
    "runtime": 207,
    "genres": [{"name": "Action"}, {"name": "Drama"}],
    "overview": "A samurai answers a village's request for protection.",
    "poster_path": "/8OKmBV5BUFzmozIC3pPWKHy17kx.jpg",
    "vote_average": 8.5,
    "credits": {"cast": [], "crew": [{"name": "Akira Kurosawa", "job": "Director"}]},
    "keywords": {"keywords": []},
    "videos": {"results": []},
}

MOVIES = {348: ALIEN, 346: SEVEN_SAMURAI}


class FakeTMDBServer:
    """Answers like api.themoviedb.org; records every request."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.fail_with: int | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_with:
            return httpx.Response(self.fail_with, json={"status_message": "nope"})
        path = request.url.path.removeprefix("/3")
        if path == "/search/movie":
            query = request.url.params["query"].lower()
            year = request.url.params.get("year")
            hits = [
                m
                for m in MOVIES.values()
                if query in m["title"].lower() and (not year or m["release_date"].startswith(year))
            ]
            return httpx.Response(200, json={"results": hits})
        if path.endswith("/videos"):
            return httpx.Response(
                200,
                json={"results": [{"site": "YouTube", "key": "samuraiJP01", "type": "Trailer"}]},
            )
        if path.startswith("/movie/"):
            movie = MOVIES.get(int(path.split("/")[2]))
            if movie is None:
                return httpx.Response(404, json={})
            return httpx.Response(200, json=movie)
        return httpx.Response(404, json={})

    def client(self) -> TMDB:
        return TMDB("test-token", transport=httpx.MockTransport(self.handler))


class FakeTagger:
    """Records what it was shown; answers with fixed tags or fails."""

    def __init__(self, error: str | None = None):
        self.seen: list[dict] = []
        self.error = error

    async def tag(self, facts: dict) -> Tags:
        self.seen.append(json.loads(json.dumps(facts)))
        if self.error:
            raise TaggerError(self.error)
        return Tags(
            moods=["tense", "dark"],
            attention="normal",
            violence=2,
            scariness=3,
            heaviness=1,
            blurb="A crew, a ship, and something in the vents.",
        )

    async def close(self) -> None:
        pass
