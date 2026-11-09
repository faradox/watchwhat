# watchwhat

"What movie could we watch tonight?" A small shared movie list for one
household, with a recommender that shows one matching movie at a time.

- **Tonight** (public): pick a mood, a time budget ("we have until 23:00"),
  decades, genres, how much attention you have left, how much violence,
  scariness or heaviness you can take. Then flip through the matches in a
  random order: poster, blurb, tags, trailer, IMDb. Movies marked "top of the
  list" come up more often.
- **Add** (logged in): type a title, optionally the year. Pick the right match
  from TMDB, and an LLM (Claude Haiku) suggests the tags and a spoiler-free
  blurb. Check, edit, save. Facts always come from TMDB, never from the model.
- **Seen** (logged in): mark who has seen a movie, one person or both at once.
  Logged in, the recommender hides what you have seen (or what one of you has
  not seen). Visitors never see this.
- **The list** (public): everything, searchable; editing when logged in.

Status: v1 written 2026-11-09. Plan and decisions: [`docs/plans/v1.md`](docs/plans/v1.md).

## Run it

With Docker:

```sh
make run-dev     # backend on :8000 (SQLite, logged in), web app on :3000 with hot reload
```

In development you are logged in as the first name in
`WATCHWHAT_DEV_ALLOWED_USERS` (default `me,partner`). Set
`WATCHWHAT_DEV_TMDB_TOKEN` and `WATCHWHAT_DEV_ANTHROPIC_API_KEY` to try the
add flow with real data; without them, movies are entered by hand and come
without tags.

Production: `make build && make run`, with settings below. The web app on
port 8103 serves the API under `/api` too, so a standalone install needs one
port behind your HTTPS proxy. The simplest login is the backend's own:

```sh
WATCHWHAT_AUTH_MODE=basic WATCHWHAT_BASIC_PASSWORD='12 or more chars' \
  WATCHWHAT_ALLOWED_USERS=me,partner make run
```

Without Docker: Python 3.12 and Node 22.

```sh
cd backend && pip install -r requirements-dev.txt && mkdir -p data
ENVIRONMENT=development DATABASE_URL=sqlite:///data/watchwhat-dev.db ALLOWED_USERS=me,partner alembic upgrade head
ENVIRONMENT=development DATABASE_URL=sqlite:///data/watchwhat-dev.db ALLOWED_USERS=me,partner python main.py
cd frontend && npm install && npm run dev    # proxies /api to localhost:8000
```

## Configuration

The compose file maps `WATCHWHAT_`-prefixed host variables to the plain names
the backend reads (`WATCHWHAT_TMDB_TOKEN` -> `TMDB_TOKEN`).

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/watchwhat`, or the default SQLite file in the data dir |
| `AUTH_MODE` | who may add and edit: `proxy` (a login proxy sets `Remote-User` + `X-Proxy-Secret`), `basic` (HTTP Basic, checked by the backend), `none` |
| `ALLOWED_USERS` | the household's login names, comma-separated; "seen" is tracked for each |
| `DISPLAY_NAMES` | optional, e.g. `felix=Felix,sam=Sam` |
| `PROXY_SECRET` | for `proxy`: the secret the proxy adds to every request |
| `BASIC_PASSWORD` | for `basic`: the shared password (12+ characters) |
| `TMDB_TOKEN` | TMDB "API Read Access Token" (free: themoviedb.org, Settings, API) |
| `ANTHROPIC_API_KEY` | for tag suggestions; without it, drafts have no tags |
| `LLM_MODEL`, `LLM_EFFORT` | default `claude-haiku-5-5`, `low` |

The recommender and the list are public in every mode. Only
`/api/private/...` needs a login. With `basic`, the "Log in" link
(`/api/private/login`) asks for the password; nothing else ever shows the
browser's login dialog.

### Behind a login proxy (`AUTH_MODE=proxy`)

Route `/api/private/` through your login (for example nginx `auth_request`
with Authelia), add `X-Proxy-Secret`, pass the user as `Remote-User`, and send
`= /api/private/login` through the same login with a redirect to the login
page instead of a 401. Everything else goes to the web app without a login,
with `Remote-User` cleared.

## Costs

Tagging one movie is one Claude Haiku call with about 1,500 tokens in and 150
out: well under a tenth of a cent. Nothing else calls the model; the public
pages never do.

## Tests

```sh
cd backend && python -m pytest -q    # or make test-dev / make test-unit
cd frontend && npm test              # filter, time budget, URL and shuffle logic
```

The backend tests run on SQLite through the real migrations with fakes for
TMDB and the model; creating a real Anthropic client fails the test run.
`make try-tagging TMDB_ID=348` tags one movie with the real model (asks
first; a fraction of a cent).

## Credits

Movie facts and posters from [TMDB](https://www.themoviedb.org/). This product
uses the TMDB API but is not endorsed or certified by TMDB.

MIT licensed, see [LICENSE](LICENSE).
