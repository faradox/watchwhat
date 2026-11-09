import base64

import pytest

from tests.conftest import PROXY_SECRET, as_user, make_client, make_settings


def basic(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_public_endpoints_need_no_login(client, add_movie):
    add_movie()
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/vocab").status_code == 200
    assert len(client.get("/api/movies").json()) == 1


def test_proxy_requires_the_secret(client):
    assert client.get("/api/private/me", headers={"Remote-User": "felix"}).status_code == 401
    wrong = {"Remote-User": "felix", "X-Proxy-Secret": "wrong"}
    assert client.get("/api/private/me", headers=wrong).status_code == 401
    no_user = {"X-Proxy-Secret": PROXY_SECRET}
    assert client.get("/api/private/me", headers=no_user).status_code == 401


def test_proxy_rejects_users_outside_the_household(client):
    assert client.get("/api/private/me", headers=as_user("mallory")).status_code == 403


def test_me_lists_the_household(client):
    me = client.get("/api/private/me", headers=as_user("sam")).json()
    assert me["user"] == {"name": "sam", "display_name": "Sam"}
    assert me["household"] == [
        {"name": "felix", "display_name": "Felix"},
        {"name": "sam", "display_name": "Sam"},
    ]
    assert me["tmdb"] is True and me["tagging"] is True


def test_me_reports_missing_helpers(settings):
    with make_client(settings) as c:
        me = c.get("/api/private/me", headers=as_user()).json()
    assert me["tmdb"] is False and me["tagging"] is False


def test_login_redirects_home(client):
    res = client.get("/api/private/login", headers=as_user(), follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/"


def test_basic_mode_asks_only_on_login(tmp_path):
    settings = make_settings(tmp_path, auth_mode="basic", basic_password="correct horse battery")
    with make_client(settings) as c:
        # The public page probing /me must not make the browser show a dialog.
        res = c.get("/api/private/me")
        assert res.status_code == 401
        assert "www-authenticate" not in res.headers
        res = c.get("/api/private/login", follow_redirects=False)
        assert res.status_code == 401
        assert res.headers["www-authenticate"].startswith("Basic")
        good = basic("sam", "correct horse battery")
        assert c.get("/api/private/login", headers=good, follow_redirects=False).status_code == 303
        assert c.get("/api/private/me", headers=good).json()["user"]["name"] == "sam"
        assert c.get("/api/private/me", headers=basic("sam", "wrong")).status_code == 401
        stranger = basic("mallory", "correct horse battery")
        assert c.get("/api/private/me", headers=stranger).status_code == 401


def test_none_mode_logs_everyone_in_as_the_first_member(tmp_path):
    settings = make_settings(tmp_path, auth_mode="none", allowed_users=())
    with make_client(settings) as c:
        me = c.get("/api/private/me").json()
    assert me["user"]["name"] == "local"
    assert [p["name"] for p in me["household"]] == ["local"]


def test_dev_proxy_without_secret_trusts_the_header(tmp_path):
    settings = make_settings(tmp_path, proxy_secret="")
    with make_client(settings) as c:
        assert c.get("/api/private/me").json()["user"]["name"] == "felix"
        sam = c.get("/api/private/me", headers={"Remote-User": "sam"}).json()
        assert sam["user"]["name"] == "sam"


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_writes_from_other_sites_are_refused(client, headers):
    body = {"title": "Anything"}
    res = client.post("/api/private/movies", json=body, headers={**as_user(), **headers})
    assert res.status_code == 403
    assert client.get("/api/private/movies", headers=as_user()).json() == []


def test_writes_from_our_own_page_pass(client):
    headers = {**as_user(), "Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"}
    res = client.post("/api/private/movies", json={"title": "Anything"}, headers=headers)
    assert res.status_code == 201


@pytest.mark.parametrize(
    "overrides, message",
    [
        (dict(proxy_secret=""), "PROXY_SECRET"),
        (dict(allowed_users=()), "ALLOWED_USERS"),
        (dict(auth_mode="basic", basic_password="short"), "BASIC_PASSWORD"),
        (dict(auth_mode="basic", basic_password="long enough password", allowed_users=()), "ALLOWED_USERS"),
        (dict(auth_mode="nonsense"), "AUTH_MODE"),
    ],
)
def test_production_refuses_half_configured_logins(tmp_path, overrides, message):
    settings = make_settings(
        tmp_path,
        environment="production",
        database_url="postgresql+asyncpg://u:p@localhost/watchwhat",
        **overrides,
    )
    with pytest.raises(RuntimeError, match=message):
        settings.validate()


def test_production_may_use_sqlite(tmp_path):
    # One household's list fits in a file; standalone installs need no Postgres.
    make_settings(tmp_path, environment="production").validate()
