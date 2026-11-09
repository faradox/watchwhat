# AGENTS.md

How to work on watchwhat, for people and coding agents alike. `README.md` says
what it is and how to run it; this file is about changing the code safely.

## Ground rules

1. **Public pages never show private data.** Seen status, who added a movie,
   and "never suggest" movies are only in `/api/private/...` answers
   (`PrivateMovieOut`). `/api/movies` uses `MovieOut`. Tests in
   `tests/test_movies.py` check this; keep them passing.
2. **Facts come from TMDB or a person, never from the model.** The model
   only picks moods, attention and intensity from the fixed lists in
   `backend/app/vocab.py` and writes the blurb. Its answer is validated again
   in `tagger.clean()`.
3. **The model costs money.** The free tests never call it (creating a real
   client fails the run). `scripts/try_tagging.py` is the only path to the
   real API outside the app, and it asks first; do not add a way around that,
   and do not run it yourself.
4. **No secrets in code, logs or tests.** Tokens and keys come from the
   environment and are never logged. Only token counts and the estimated cost
   of a tagging call are.
5. **Every schema change is a new Alembic migration.** Never edit one that
   has run anywhere.

## Layout

```text
backend/
  main.py, config.py      app factory (TMDB and tagger are injectable); settings
  app/
    models.py, db.py      movie, seen (SQLAlchemy 2, async)
    vocab.py              the fixed tag lists: one source for validation, the model and the UI
    schemas.py            API shapes; public vs. private answers
    auth.py               proxy / basic / none; same-origin check for writes
    tmdb.py               TMDB search and facts (httpx)
    tagger.py, tagging.py the model call (structured output) and its glue
    api/                  public.py, private.py, add.py
  alembic/versions/       migrations
  tests/                  pytest; fakes.py holds the TMDB and tagger stand-ins
  scripts/try_tagging.py  PAID single tagging run, asks first
frontend/
  src/App.jsx, api.js     shell, loading, the only API client
  src/lib/filters.js      matching, time budget, URL form, weighted shuffle (tested)
  src/pages/              Tonight, Library, Movie, Add, MovieEditor
  src/components/         MovieCard, FilterPanel, SeenControl, Poster, ui.jsx
docs/plans/v1.md          plan and decision log
```

## Changing things

- **A new mood or attention level:** add it to `app/vocab.py`. The model's
  schema, its prompt, validation and the UI pick it up. Renaming or removing
  a value needs a data migration for stored movies.
- **A new filter:** `frontend/src/lib/filters.js` (matching and the URL form,
  with a test in `filters.test.js`), then `FilterPanel.jsx`.
- **The model prompt:** `SYSTEM` in `app/tagger.py`. Check a few movies with
  `make try-tagging` (the maintainer runs it) before and after.
- **Auth:** `/api/private/me` must answer 401 without a Basic challenge, or
  every visitor gets a browser login dialog (`test_basic_mode_asks_only_on_login`).

## Verifying

```sh
cd backend && python -m pytest -q
cd frontend && npm test && npm run build
```

Look at the pages at phone width (390 px): Tonight logged in and out, the
list, adding a movie, editing one.

## Conventions

- Python: Black (88 columns), async SQLAlchemy, snake_case. JavaScript:
  Prettier, 2-space indent, PascalCase components.
- Keep files under 500 lines. No emojis in code, comments or logs.
- Comments say why, not what. Record decisions in the plan's decision log.

## In the maintainer's environment

watchwhat started inside the maintainer's server monorepo ("breathdance").
When you work there: do not read secrets or root-owned files, do not run
commands on the server (write them for the maintainer), and treat git as
read-only. The laptop has no project-local installs: verify the backend with
the system Python (`PYTHONNOUSERSITE=1`, `sniffio` and `greenlet` from
`~/.local` on `PYTHONPATH`) and the frontend with Vite, Tailwind, React and
vitest borrowed from sibling projects' `node_modules`.
