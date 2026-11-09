import { useMemo, useState } from "react";
import Poster from "../components/Poster.jsx";
import { LinkButton, Tag, inputClass } from "../components/ui.jsx";
import { runtimeLabel, titles } from "../lib/links.js";
import { labeler } from "../lib/vocab.js";

const SORTS = {
  added: { label: "Newest", fn: (a, b) => b.created_at.localeCompare(a.created_at) },
  title: { label: "Title", fn: (a, b) => titles(a).main.localeCompare(titles(b).main) },
  year: { label: "Year", fn: (a, b) => (b.year || 0) - (a.year || 0) },
};

function haystack(movie) {
  return [movie.title, movie.original_title, movie.director, ...movie.cast, ...movie.keywords, movie.year]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

// Every movie on the list, searchable. Logged in, also the hidden ones and who has seen what.
export default function LibraryPage({ movies, vocab, me }) {
  const label = labeler(vocab);
  const [text, setText] = useState("");
  const [sort, setSort] = useState("added");
  const shown = useMemo(() => {
    const words = text.toLowerCase().split(/\s+/).filter(Boolean);
    return movies.filter((m) => words.every((w) => haystack(m).includes(w))).sort(SORTS[sort].fn);
  }, [movies, text, sort]);
  const names = Object.fromEntries((me?.household || []).map((p) => [p.name, p.display_name]));

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-semibold text-mist-100">The list</h1>
          <p className="text-sm text-mist-400">{movies.length} movies</p>
        </div>
        {me && (
          <LinkButton kind="primary" href="#/add">
            + Add a movie
          </LinkButton>
        )}
      </header>

      <div className="flex gap-2">
        <input
          type="search"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Search title, people, year"
          aria-label="Search the list"
          className={inputClass}
        />
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className={`${inputClass} w-auto!`}>
          {Object.entries(SORTS).map(([key, s]) => (
            <option key={key} value={key}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {shown.length === 0 && <p className="text-sm text-mist-400">Nothing found.</p>}

      <ul className="divide-y divide-night-700 overflow-hidden rounded-3xl border border-night-700 bg-night-800/60">
        {shown.map((movie) => {
          const { main, sub } = titles(movie);
          const seenBy = movie.seen_by || [];
          return (
            <li key={movie.id}>
              <a href={`#/movie/${movie.id}`} className="flex gap-3 p-3 transition hover:bg-night-700/60 sm:gap-4">
                <Poster path={movie.poster_path} title={main} size="w154" className="w-14 flex-none rounded-lg sm:w-16" />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="truncate font-medium text-mist-100">
                    {movie.priority && <span className="text-gold-400">{"★"} </span>}
                    {main}
                    {sub && <span className="font-normal text-mist-400"> · {sub}</span>}
                  </p>
                  <p className="text-xs text-mist-400">
                    {[movie.year, runtimeLabel(movie.runtime_min), movie.director].filter(Boolean).join(" · ")}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {movie.moods.map((m) => (
                      <Tag key={m} tone="gold">
                        {label.mood(m)}
                      </Tag>
                    ))}
                    {movie.never_suggest && <Tag>Never suggested</Tag>}
                    {seenBy.length > 0 && (
                      <Tag tone="coral">
                        {"✓"} {seenBy.length === (me?.household.length || 0) && seenBy.length > 1
                          ? "Seen by both"
                          : `Seen by ${seenBy.map((n) => names[n] || n).join(", ")}`}
                      </Tag>
                    )}
                  </div>
                </div>
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
