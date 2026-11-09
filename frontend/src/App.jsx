import { useCallback, useEffect, useState } from "react";
import { LOGIN_URL, api } from "./api.js";
import { Button, Notice, Spinner } from "./components/ui.jsx";
import { useRoute } from "./lib/router.js";
import AddPage from "./pages/AddPage.jsx";
import LibraryPage from "./pages/LibraryPage.jsx";
import MoviePage from "./pages/MoviePage.jsx";
import TonightPage from "./pages/TonightPage.jsx";

const NAV = [
  { page: "tonight", href: "#/", label: "Tonight" },
  { page: "library", href: "#/library", label: "The list" },
  { page: "add", href: "#/add", label: "Add", loggedIn: true },
];

export default function App() {
  const route = useRoute();
  const [vocab, setVocab] = useState(null);
  // undefined while loading, null for visitors.
  const [me, setMe] = useState(undefined);
  const [movies, setMovies] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [v, who] = await Promise.all([api.vocab(), api.me()]);
      setVocab(v);
      setMe(who);
      setMovies(who ? await api.movies() : await api.publicMovies());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const replace = (movie) => setMovies((list) => [movie, ...list.filter((m) => m.id !== movie.id)].sort((a, b) => b.created_at.localeCompare(a.created_at)));

  const change = async (movie, call) => {
    setBusyId(movie.id);
    setError(null);
    try {
      replace(await call());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };
  const onSeen = (movie, users) => {
    // Show it at once; the answer from the server replaces it.
    replace({ ...movie, seen_by: users });
    change(movie, () => api.setSeen(movie.id, users));
  };
  const onFlags = (movie, flags) => change(movie, () => api.setFlags(movie.id, flags));
  const onDeleted = (movie) => setMovies((list) => list.filter((m) => m.id !== movie.id));

  const ready = vocab && movies && me !== undefined;
  const pageProps = { movies, vocab, me, onSeen, onFlags, busyId };

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col px-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <header className="mb-6 flex items-center justify-between gap-3">
        <a href="#/" className="flex items-center gap-2 font-display text-lg font-semibold text-mist-100">
          <img src="/favicon.svg" alt="" className="h-7 w-7" />
          watchwhat
        </a>
        <nav className="flex items-center gap-1 text-sm">
          {NAV.filter((item) => !item.loggedIn || me).map((item) => {
            const on = route.page === item.page || (item.page === "library" && route.page === "movie");
            return (
              <a
                key={item.page}
                href={item.href}
                aria-current={on ? "page" : undefined}
                className={`rounded-lg px-3 py-2 transition ${on ? "bg-night-700 text-mist-100" : "text-mist-400 hover:text-mist-100"}`}
              >
                {item.label}
              </a>
            );
          })}
          {me === null && (
            <a href={LOGIN_URL} className="rounded-lg px-3 py-2 text-mist-400 hover:text-mist-100">
              Log in
            </a>
          )}
        </nav>
      </header>

      <main className="flex-1">
        {error && (
          <div className="mb-4">
            <Notice tone="error">
              {error}{" "}
              {!ready && (
                <Button kind="ghost" className="ml-2 min-h-8" onClick={load}>
                  Try again
                </Button>
              )}
            </Notice>
          </div>
        )}
        {!ready && !error && <Spinner label="Loading the list..." />}
        {ready && route.page === "tonight" && <TonightPage query={route.query} {...pageProps} />}
        {ready && route.page === "library" && <LibraryPage movies={movies} vocab={vocab} me={me} />}
        {ready && route.page === "add" && <AddPage me={me} vocab={vocab} onSaved={replace} />}
        {ready && route.page === "movie" && (
          <MoviePage id={route.id} sub={route.sub} query={route.query} onSaved={replace} onDeleted={onDeleted} {...pageProps} />
        )}
        {ready && !["tonight", "library", "add", "movie"].includes(route.page) && (
          <Notice>
            No such page.{" "}
            <a className="text-gold-300 underline" href="#/">
              Back to tonight
            </a>
          </Notice>
        )}
      </main>

      <footer className="mt-10 space-y-1 text-center text-xs text-night-500">
        <p>
          {me ? `Logged in as ${me.user.display_name}. ` : ""}
          Movie facts and posters from{" "}
          <a href="https://www.themoviedb.org/" target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:text-mist-400">
            TMDB
          </a>
          .
        </p>
        <p>This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
      </footer>
    </div>
  );
}
