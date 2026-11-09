import { useState } from "react";
import { imdbUrl, languageLabel, runtimeLabel, titles, trailerUrl } from "../lib/links.js";
import { labeler } from "../lib/vocab.js";
import Poster from "./Poster.jsx";
import SeenControl from "./SeenControl.jsx";
import { LinkButton, Tag } from "./ui.jsx";

// One movie, the way the recommender and the movie page show it.
// `me` is null for visitors: no seen marks, no editing.
export default function MovieCard({ movie, vocab, me, onSeen, onFlags, busy, footer }) {
  const label = labeler(vocab);
  const { main, sub } = titles(movie);
  const [showPlot, setShowPlot] = useState(false);
  const meta = [
    movie.year,
    runtimeLabel(movie.runtime_min),
    movie.original_language && movie.original_language !== "en" ? languageLabel(movie.original_language) : null,
    movie.director,
  ].filter(Boolean);
  const intensity = ["violence", "scariness", "heaviness"]
    .filter((key) => movie[key] != null)
    .map((key) => `${label.scale(key)}: ${label.level(key, movie[key]).toLowerCase()}`);
  const imdb = imdbUrl(movie);
  const blurb = movie.blurb || movie.overview;

  return (
    <article className="animate-rise overflow-hidden rounded-3xl border border-night-700 bg-night-800/80 shadow-2xl shadow-black/40">
      <div className="grid gap-0 sm:grid-cols-[minmax(0,15rem)_1fr]">
        <div className="relative">
          <Poster
            path={movie.poster_path}
            title={main}
            // Without a poster, phones skip the empty block; wider screens keep the column.
            className={`h-full w-full max-sm:max-h-[26rem] ${movie.poster_path ? "" : "max-sm:hidden"}`}
          />
          {movie.priority && (
            <span
              className={`rounded-full bg-gold-400 px-2.5 py-1 text-xs font-semibold text-night-950 ${
                movie.poster_path ? "absolute top-3 left-3" : "absolute top-3 left-3 max-sm:static max-sm:m-5 max-sm:mb-0 max-sm:inline-block"
              }`}
            >
              {"★"} Top of the list
            </span>
          )}
        </div>

        <div className="flex flex-col gap-4 p-5 sm:p-6">
          <header>
            <h2 className="font-display text-2xl leading-tight font-semibold text-mist-100 sm:text-3xl" lang={movie.original_language || undefined}>
              {main}
            </h2>
            {sub && <p className="mt-1 text-mist-300">{sub}</p>}
            {meta.length > 0 && <p className="mt-2 text-sm text-mist-400">{meta.join(" · ")}</p>}
          </header>

          {blurb && <p className="text-base leading-relaxed text-mist-100">{blurb}</p>}

          <div className="flex flex-wrap gap-1.5">
            {movie.moods.map((m) => (
              <Tag key={m} tone="gold">
                {label.mood(m)}
              </Tag>
            ))}
            {movie.attention && <Tag tone="coral">{label.attention(movie.attention)}</Tag>}
            {movie.genres.map((g) => (
              <Tag key={g}>{g}</Tag>
            ))}
          </div>

          {intensity.length > 0 && <p className="text-xs text-mist-400">{intensity.join(" · ")}</p>}

          {movie.blurb && movie.overview && (
            <div>
              <button
                type="button"
                className="text-sm text-mist-400 underline decoration-night-600 underline-offset-4 hover:text-mist-100"
                aria-expanded={showPlot}
                onClick={() => setShowPlot(!showPlot)}
              >
                {showPlot ? "Hide the plot" : "What's it about?"}
              </button>
              {showPlot && <p className="mt-2 text-sm leading-relaxed text-mist-300">{movie.overview}</p>}
            </div>
          )}

          <div className="mt-auto flex flex-wrap gap-2 pt-1">
            <LinkButton kind="primary" href={trailerUrl(movie)} target="_blank" rel="noreferrer">
              {"▶"} {movie.trailer_youtube_key ? "Trailer" : "Find a trailer"}
            </LinkButton>
            {imdb && (
              <LinkButton href={imdb} target="_blank" rel="noreferrer">
                IMDb
              </LinkButton>
            )}
            {me && (
              <LinkButton href={`#/movie/${movie.id}/edit`} aria-label={`Edit ${main}`}>
                Edit
              </LinkButton>
            )}
          </div>

          {me && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-night-700 pt-4">
              <SeenControl
                seenBy={movie.seen_by || []}
                household={me.household}
                onChange={(users) => onSeen?.(movie, users)}
                busy={busy}
              />
              <button
                type="button"
                onClick={() => onFlags?.(movie, { priority: !movie.priority })}
                aria-pressed={movie.priority}
                className={`text-sm transition ${movie.priority ? "text-gold-400" : "text-mist-400 hover:text-gold-300"}`}
                title="We both really want to see this: it comes up more often"
              >
                {movie.priority ? "★ Top of the list" : "☆ Top of the list"}
              </button>
            </div>
          )}
          {!movie.verified && <p className="text-xs text-mist-400">Entered by hand, not checked against TMDB.</p>}
          {footer}
        </div>
      </div>
    </article>
  );
}
