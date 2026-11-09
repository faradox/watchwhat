from tests.conftest import as_user, make_client
from tests.fakes import FakeTagger


def test_search_finds_candidates(client, tmdb_server):
    res = client.get("/api/private/tmdb/search", params={"q": "alien"}, headers=as_user())
    assert res.status_code == 200
    [alien] = res.json()
    assert alien["tmdb_id"] == 348
    assert alien["year"] == 1979
    assert alien["on_list"] is None
    request = tmdb_server.requests[0]
    assert request.headers["authorization"] == "Bearer test-token"
    assert request.url.params["include_adult"] == "false"


def test_search_marks_movies_already_on_the_list(client, add_movie):
    saved = add_movie(tmdb_id=348, title="Alien")
    [alien] = client.get("/api/private/tmdb/search", params={"q": "alien"}, headers=as_user()).json()
    assert alien["on_list"] == saved["id"]


def test_a_wrong_year_does_not_hide_the_movie(client, tmdb_server):
    res = client.get("/api/private/tmdb/search", params={"q": "alien", "year": 1986}, headers=as_user())
    assert [c["tmdb_id"] for c in res.json()] == [348]
    assert tmdb_server.requests[0].url.params["year"] == "1986"
    assert "year" not in tmdb_server.requests[1].url.params


def test_search_needs_a_login(client):
    assert client.get("/api/private/tmdb/search", params={"q": "alien"}).status_code == 401


def test_search_without_tmdb(settings):
    with make_client(settings) as c:
        res = c.get("/api/private/tmdb/search", params={"q": "alien"}, headers=as_user())
    assert res.status_code == 503
    assert "by hand" in res.json()["detail"]


def test_tmdb_errors_are_explained(client, tmdb_server):
    tmdb_server.fail_with = 401
    res = client.get("/api/private/tmdb/search", params={"q": "alien"}, headers=as_user())
    assert res.status_code == 502
    assert res.json()["detail"] == "TMDB rejected the token."


def test_draft_from_tmdb(client, tagger):
    res = client.post("/api/private/drafts", json={"tmdb_id": 348}, headers=as_user())
    assert res.status_code == 200
    draft = res.json()
    assert draft["title"] == "Alien"
    assert draft["year"] == 1979
    assert draft["runtime_min"] == 117
    assert draft["imdb_id"] == "tt0078748"
    assert draft["genres"] == ["Horror", "Science Fiction"]
    assert draft["director"] == "Ridley Scott"
    assert draft["cast"] == ["Sigourney Weaver", "Tom Skerritt"]
    assert draft["keywords"] == ["space", "android"]
    # Official trailer beats the teaser and the fan-made one; Vimeo is ignored.
    assert draft["trailer_youtube_key"] == "LjLamj-b0I8"
    assert draft["verified"] is True
    assert draft["moods"] == ["tense", "dark"]
    assert draft["scariness"] == 3
    assert draft["blurb"].startswith("A crew")
    assert draft["tag_error"] is None
    assert draft["already_on_list"] is None
    # The model sees facts only.
    [facts] = tagger.seen
    assert facts["title"] == "Alien"
    assert facts["director"] == "Ridley Scott"
    assert "moods" not in facts and "priority" not in facts


def test_draft_can_be_saved_as_it_is(client):
    draft = client.post("/api/private/drafts", json={"tmdb_id": 348}, headers=as_user()).json()
    body = {k: v for k, v in draft.items() if k not in ("tag_error", "already_on_list")}
    res = client.post("/api/private/movies", json=body, headers=as_user())
    assert res.status_code == 201
    assert res.json()["tmdb_id"] == 348


def test_draft_for_a_film_in_another_language(client, tmdb_server):
    draft = client.post("/api/private/drafts", json={"tmdb_id": 346}, headers=as_user()).json()
    assert draft["title"] == "Seven Samurai"
    assert draft["original_title"] == "七人の侍"
    assert draft["original_language"] == "ja"
    # No English trailer: asked again in Japanese.
    assert draft["trailer_youtube_key"] == "samuraiJP01"
    videos = tmdb_server.requests[-1]
    assert videos.url.path.endswith("/346/videos")
    assert videos.url.params["include_video_language"] == "ja,null"


def test_draft_for_a_movie_already_on_the_list_costs_nothing(client, tagger, add_movie):
    saved = add_movie(tmdb_id=348, title="Alien")
    draft = client.post("/api/private/drafts", json={"tmdb_id": 348}, headers=as_user()).json()
    assert draft["already_on_list"] == saved["id"]
    assert tagger.seen == []


def test_draft_without_tagging(settings, tmdb_server):
    with make_client(settings, tmdb_server, None) as c:
        draft = c.post("/api/private/drafts", json={"tmdb_id": 348}, headers=as_user()).json()
    assert draft["title"] == "Alien"
    assert draft["moods"] == []
    assert draft["blurb"] is None
    assert "no Anthropic API key" in draft["tag_error"]


def test_draft_when_tagging_fails(settings, tmdb_server):
    with make_client(settings, tmdb_server, FakeTagger(error="rate_limited")) as c:
        draft = c.post("/api/private/drafts", json={"tmdb_id": 348}, headers=as_user()).json()
    assert draft["moods"] == []
    assert "busy" in draft["tag_error"]


def test_draft_for_an_unknown_tmdb_id(client):
    res = client.post("/api/private/drafts", json={"tmdb_id": 999}, headers=as_user())
    assert res.status_code == 404


def test_manual_draft(client, tagger):
    body = {"title": "Our wedding video", "year": 2019, "runtime_min": 95}
    draft = client.post("/api/private/drafts", json=body, headers=as_user()).json()
    assert draft["title"] == "Our wedding video"
    assert draft["verified"] is False
    assert draft["tmdb_id"] is None
    assert draft["moods"] == ["tense", "dark"]
    assert tagger.seen[0]["year"] == 2019


def test_manual_draft_needs_a_title(client):
    assert client.post("/api/private/drafts", json={"year": 2000}, headers=as_user()).status_code == 422


def test_retag_suggests_without_saving(client, add_movie, tagger):
    movie = add_movie(moods=["cozy"])
    res = client.post(f"/api/private/movies/{movie['id']}/retag", headers=as_user())
    assert res.status_code == 200
    assert res.json()["moods"] == ["tense", "dark"]
    assert tagger.seen[0]["title"] == "Paddington 2"
    stored = client.get(f"/api/private/movies/{movie['id']}", headers=as_user()).json()
    assert stored["moods"] == ["cozy"]


def test_retag_without_a_key(settings, add_movie):
    with make_client(settings) as c:
        res = c.post("/api/private/movies", json={"title": "X"}, headers=as_user())
        res = c.post(f"/api/private/movies/{res.json()['id']}/retag", headers=as_user())
    assert res.status_code == 503
