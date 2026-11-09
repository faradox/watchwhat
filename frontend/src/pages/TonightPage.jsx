import { useEffect, useMemo, useState } from "react";
import { LOGIN_URL } from "../api.js";
import FilterPanel from "../components/FilterPanel.jsx";
import MovieCard from "../components/MovieCard.jsx";
import { Button, LinkButton, Notice } from "../components/ui.jsx";
import { decadeOf, filtersFromQuery, filtersToQuery, matches, newSeed, shuffle } from "../lib/filters.js";
import { replaceQuery } from "../lib/router.js";

// The recommender: filters on top, one movie at a time in a weighted random order.
export default function TonightPage({ query, movies, vocab, me, onSeen, onFlags, busyId }) {
  const filters = useMemo(() => filtersFromQuery(query), [query]);
  const [seed, setSeed] = useState(newSeed);
  const loggedIn = Boolean(me);

  const decades = useMemo(
    () => [...new Set(movies.map((m) => decadeOf(m.year)).filter(Boolean))].sort((a, b) => a - b),
    [movies],
  );
  const genres = useMemo(() => {
    const present = new Set(movies.flatMap((m) => m.genres));
    return vocab.genres.filter((g) => present.has(g));
  }, [movies, vocab]);

  const order = useMemo(() => {
    const now = new Date();
    return shuffle(
      movies.filter((m) => matches(m, filters, { loggedIn, now })),
      seed,
    );
  }, [movies, filters, loggedIn, seed]);

  // Where we are in this shuffle. A new filter or shuffle starts over; marking
  // the current movie as seen keeps it on screen until "Next".
  const key = `${query}|${seed}`;
  const [nav, setNav] = useState({ key, ids: [], cursor: 0 });
  const ids = nav.key === key && nav.ids.length ? nav.ids : order[0] ? [order[0].id] : [];
  const cursor = nav.key === key ? nav.cursor : 0;
  const byId = useMemo(() => new Map(movies.map((m) => [m.id, m])), [movies]);
  const current = byId.get(ids[cursor]);
  const finished = order.length > 0 && cursor >= ids.length;

  const next = () => {
    if (cursor < ids.length - 1) return setNav({ key, ids, cursor: cursor + 1 });
    const upcoming = order.find((m) => !ids.includes(m.id));
    setNav({ key, ids: upcoming ? [...ids, upcoming.id] : ids, cursor: cursor + 1 });
  };
  const previous = () => cursor > 0 && setNav({ key, ids, cursor: cursor - 1 });
  const reshuffle = () => setSeed(newSeed());

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.closest("input, select, textarea")) return;
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") previous();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="font-display text-3xl font-semibold text-mist-100 sm:text-4xl">What do we watch tonight?</h1>
        <p className="text-sm text-mist-400" aria-live="polite">
          {movies.length === 0
            ? "The list is still empty."
            : `${order.length} of ${movies.filter((m) => !m.never_suggest).length} movies match.`}
        </p>
      </header>

      <FilterPanel
        filters={filters}
        onChange={(f) => replaceQuery("/", filtersToQuery(f))}
        vocab={vocab}
        me={me}
        decades={decades}
        genres={genres}
      />

      {movies.length === 0 ? (
        <Notice>
          Nothing on the list yet.{" "}
          {me ? (
            <a className="text-gold-300 underline" href="#/add">
              Add the first movie
            </a>
          ) : (
            "Come back soon."
          )}
        </Notice>
      ) : order.length === 0 && !current ? (
        <Notice>Nothing matches all of that. Take a filter or two away.</Notice>
      ) : finished ? (
        <div className="space-y-3 rounded-3xl border border-night-700 bg-night-800/60 p-6 text-center">
          <p className="font-display text-xl text-mist-100">That was all {order.length}.</p>
          <p className="text-sm text-mist-400">Still undecided? Shuffle and go around again.</p>
          <div className="flex justify-center gap-2">
            <Button onClick={previous}>Back</Button>
            <Button kind="primary" onClick={reshuffle}>
              Shuffle again
            </Button>
          </div>
        </div>
      ) : (
        current && (
          <div className="space-y-3">
            <MovieCard
              key={current.id}
              movie={current}
              vocab={vocab}
              me={me}
              onSeen={onSeen}
              onFlags={onFlags}
              busy={busyId === current.id}
            />
            <nav className="flex items-center gap-2" aria-label="Suggestions">
              <Button onClick={previous} disabled={cursor === 0} aria-label="Previous suggestion">
                {"←"}
              </Button>
              <Button kind="primary" className="flex-1 text-base" onClick={next}>
                Something else {"→"}
              </Button>
              <Button kind="ghost" onClick={reshuffle} title="New random order">
                Shuffle
              </Button>
            </nav>
            <p className="text-center text-xs text-mist-400">
              {Math.min(cursor + 1, order.length)} / {order.length}
            </p>
          </div>
        )
      )}

      {!me && movies.length > 0 && (
        <p className="text-center text-xs text-mist-400">
          Ours?{" "}
          <LinkButton kind="plain" className="ml-1 min-h-8 px-3 py-1 text-xs" href={LOGIN_URL}>
            Log in
          </LinkButton>{" "}
          to hide what we've seen.
        </p>
      )}
    </div>
  );
}
