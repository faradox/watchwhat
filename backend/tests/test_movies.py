from tests.conftest import as_user, movie_body


def test_saved_movie_shows_in_both_lists(client, add_movie):
    saved = add_movie(tmdb_id=1)
    assert saved["added_by"] == "felix"
    assert saved["seen_by"] == []
    private = client.get("/api/private/movies", headers=as_user()).json()
    assert [m["id"] for m in private] == [saved["id"]]
    public = client.get("/api/movies").json()
    assert [m["title"] for m in public] == ["Paddington 2"]


def test_public_answers_carry_no_private_fields(client, add_movie):
    movie = add_movie()
    client.put(f"/api/private/movies/{movie['id']}/seen", json={"users": ["felix"]}, headers=as_user())
    for item in (client.get("/api/movies").json()[0], client.get(f"/api/movies/{movie['id']}").json()):
        assert "seen_by" not in item
        assert "added_by" not in item
        assert "never_suggest" not in item


def test_public_requests_ignore_a_forged_user_header(client, add_movie):
    add_movie()
    item = client.get("/api/movies", headers=as_user()).json()[0]
    assert "seen_by" not in item


def test_never_suggest_hides_from_the_public(client, add_movie):
    movie = add_movie()
    res = client.patch(f"/api/private/movies/{movie['id']}", json={"never_suggest": True}, headers=as_user())
    assert res.json()["never_suggest"] is True
    assert client.get("/api/movies").json() == []
    assert client.get(f"/api/movies/{movie['id']}").status_code == 404
    assert len(client.get("/api/private/movies", headers=as_user()).json()) == 1


def test_flags_change_only_what_is_sent(client, add_movie):
    movie = add_movie()
    res = client.patch(f"/api/private/movies/{movie['id']}", json={"priority": True}, headers=as_user())
    assert res.json()["priority"] is True
    assert res.json()["never_suggest"] is False


def test_edit_replaces_the_fields(client, add_movie):
    movie = add_movie()
    body = movie_body(title="Paddington", year=2014, moods=["cozy"])
    res = client.put(f"/api/private/movies/{movie['id']}", json=body, headers=as_user())
    assert res.status_code == 200
    assert res.json()["title"] == "Paddington"
    assert res.json()["moods"] == ["cozy"]
    assert res.json()["added_by"] == "felix"


def test_delete(client, add_movie):
    movie = add_movie()
    client.put(f"/api/private/movies/{movie['id']}/seen", json={"users": ["sam"]}, headers=as_user())
    assert client.delete(f"/api/private/movies/{movie['id']}", headers=as_user()).status_code == 204
    assert client.get(f"/api/private/movies/{movie['id']}", headers=as_user()).status_code == 404
    assert client.delete(f"/api/private/movies/{movie['id']}", headers=as_user()).status_code == 404


def test_the_same_tmdb_movie_cannot_be_added_twice(client, add_movie):
    first = add_movie(tmdb_id=348)
    res = client.post("/api/private/movies", json=movie_body(tmdb_id=348), headers=as_user())
    assert res.status_code == 409
    second = add_movie(tmdb_id=346, title="Seven Samurai")
    res = client.put(
        f"/api/private/movies/{second['id']}", json=movie_body(tmdb_id=348), headers=as_user()
    )
    assert res.status_code == 409
    # Saving a movie with its own TMDB id is fine.
    res = client.put(f"/api/private/movies/{first['id']}", json=movie_body(tmdb_id=348), headers=as_user())
    assert res.status_code == 200


def test_movies_without_tmdb_id_can_share_titles(add_movie):
    add_movie(title="Home movie", verified=False)
    add_movie(title="Home movie", verified=False)


def test_links_are_reduced_to_ids(add_movie):
    movie = add_movie(
        trailer_youtube_key="https://www.youtube.com/watch?v=52x5HJ9H8DM&t=3s",
        imdb_id="https://www.imdb.com/title/tt4468740/?ref_=nv_sr",
    )
    assert movie["trailer_youtube_key"] == "52x5HJ9H8DM"
    assert movie["imdb_id"] == "tt4468740"


def test_short_youtube_links_work(add_movie):
    assert add_movie(trailer_youtube_key="https://youtu.be/52x5HJ9H8DM")["trailer_youtube_key"] == "52x5HJ9H8DM"


def test_blank_strings_become_null(add_movie):
    movie = add_movie(blurb="  ", trailer_youtube_key="", imdb_id="")
    assert movie["blurb"] is None
    assert movie["trailer_youtube_key"] is None
    assert movie["imdb_id"] is None


def test_validation(client):
    bad = [
        movie_body(moods=["sleepy"]),
        movie_body(moods=["funny", "cozy", "weird", "epic"]),
        movie_body(genres=["Telenovela"]),
        movie_body(attention="half"),
        movie_body(violence=4),
        movie_body(trailer_youtube_key="https://vimeo.com/123"),
        movie_body(imdb_id="nm0000123"),
        movie_body(title=""),
        movie_body(poster_path="../../etc/passwd"),
    ]
    for body in bad:
        res = client.post("/api/private/movies", json=body, headers=as_user())
        assert res.status_code == 422, body


def test_seen_per_person_and_together(client, add_movie):
    movie = add_movie()
    url = f"/api/private/movies/{movie['id']}/seen"
    assert client.put(url, json={"users": ["sam"]}, headers=as_user()).json()["seen_by"] == ["sam"]
    both = client.put(url, json={"users": ["sam", "felix"]}, headers=as_user()).json()
    assert both["seen_by"] == ["felix", "sam"]
    assert client.put(url, json={"users": ["felix"]}, headers=as_user()).json()["seen_by"] == ["felix"]
    assert client.put(url, json={"users": []}, headers=as_user()).json()["seen_by"] == []
    listed = client.get("/api/private/movies", headers=as_user()).json()[0]
    assert listed["seen_by"] == []


def test_seen_only_for_the_household(client, add_movie):
    movie = add_movie()
    res = client.put(f"/api/private/movies/{movie['id']}/seen", json={"users": ["mallory"]}, headers=as_user())
    assert res.status_code == 422


def test_seen_marks_of_former_members_are_dropped(tmp_path, add_movie, client, settings):
    movie = add_movie()
    url = f"/api/private/movies/{movie['id']}/seen"
    client.put(url, json={"users": ["sam"]}, headers=as_user())
    settings.allowed_users = ("felix",)
    res = client.put(url, json={"users": ["sam", "felix"]}, headers=as_user())
    assert res.status_code == 200
    assert res.json()["seen_by"] == ["felix"]


def test_seen_survives_a_reload(client, add_movie):
    movie = add_movie()
    client.put(f"/api/private/movies/{movie['id']}/seen", json={"users": ["felix", "sam"]}, headers=as_user())
    again = client.get(f"/api/private/movies/{movie['id']}", headers=as_user()).json()
    assert again["seen_by"] == ["felix", "sam"]
