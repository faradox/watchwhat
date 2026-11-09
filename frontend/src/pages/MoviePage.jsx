import { LOGIN_URL } from "../api.js";
import MovieCard from "../components/MovieCard.jsx";
import { Button, LinkButton, Notice } from "../components/ui.jsx";
import { tmdbUrl } from "../lib/links.js";
import MovieEditor from "./MovieEditor.jsx";

// #/movie/12 shows one movie; #/movie/12/edit edits it (logged in).
export default function MoviePage({ id, sub, query, movies, vocab, me, onSeen, onFlags, onSaved, onDeleted, busyId }) {
  const movie = movies.find((m) => m.id === id);
  if (!movie) {
    return (
      <Notice>
        This movie is not on the list (anymore).{" "}
        <a className="text-gold-300 underline" href="#/library">
          Back to the list
        </a>
      </Notice>
    );
  }

  if (sub === "edit") {
    if (!me) {
      return (
        <Notice>
          Editing is for the two of us.{" "}
          <a className="text-gold-300 underline" href={LOGIN_URL}>
            Log in
          </a>
        </Notice>
      );
    }
    return (
      <div className="space-y-4">
        <h1 className="font-display text-2xl font-semibold">Edit</h1>
        <MovieEditor
          key={movie.id}
          initial={movie}
          vocab={vocab}
          onSaved={(saved) => {
            onSaved(saved);
            window.location.hash = `#/movie/${saved.id}`;
          }}
          onDeleted={(gone) => {
            onDeleted(gone);
            window.location.hash = "#/library";
          }}
          onCancel={() => window.history.back()}
        />
      </div>
    );
  }

  const justAdded = new URLSearchParams(query).has("added");
  const tmdb = tmdbUrl(movie);
  return (
    <div className="space-y-4">
      {justAdded && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-gold-400/40 bg-gold-400/10 px-4 py-3 text-sm text-gold-300">
          Saved to the list.
          <LinkButton kind="primary" className="min-h-9" href="#/add">
            Add another
          </LinkButton>
        </div>
      )}
      <MovieCard
        movie={movie}
        vocab={vocab}
        me={me}
        onSeen={onSeen}
        onFlags={onFlags}
        busy={busyId === movie.id}
        footer={
          tmdb && (
            <a href={tmdb} target="_blank" rel="noreferrer" className="text-xs text-mist-400 underline underline-offset-4 hover:text-mist-100">
              On TMDB
            </a>
          )
        }
      />
      <Button kind="ghost" onClick={() => window.history.back()}>
        {"←"} Back
      </Button>
    </div>
  );
}
