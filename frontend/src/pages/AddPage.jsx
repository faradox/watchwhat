import { useState } from "react";
import { LOGIN_URL, api } from "../api.js";
import Poster from "../components/Poster.jsx";
import { Button, Field, Notice, Spinner, inputClass } from "../components/ui.jsx";
import { titles } from "../lib/links.js";
import MovieEditor from "./MovieEditor.jsx";

// Title (and maybe year) -> pick the TMDB match -> tagged draft -> edit -> save.
export default function AddPage({ me, vocab, onSaved }) {
  const [step, setStep] = useState(me?.tmdb ? "search" : "manual");
  const [text, setText] = useState("");
  const [year, setYear] = useState("");
  const [results, setResults] = useState(null);
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [manual, setManual] = useState({ title: "", year: "", runtime_min: "", overview: "" });

  if (!me) {
    return (
      <div className="space-y-4">
        <h1 className="font-display text-3xl font-semibold">Add a movie</h1>
        <Notice>
          Adding is for the two of us.{" "}
          <a className="text-gold-300 underline" href={LOGIN_URL}>
            Log in
          </a>
        </Notice>
      </div>
    );
  }

  const run = async (label, fn) => {
    setBusy(label);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };

  const search = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    run("Searching TMDB", async () => setResults(await api.search(text.trim(), year || undefined)));
  };

  const pick = (candidate) =>
    run(me.tagging ? "Looking it up and suggesting tags" : "Looking it up", async () => {
      setDraft(await api.draft({ tmdb_id: candidate.tmdb_id }));
      setStep("edit");
    });

  const fromManual = (e) => {
    e.preventDefault();
    const body = {
      title: manual.title.trim(),
      year: manual.year ? Number(manual.year) : null,
      runtime_min: manual.runtime_min ? Number(manual.runtime_min) : null,
      overview: manual.overview.trim() || null,
    };
    run(me.tagging ? "Suggesting tags" : "Preparing", async () => {
      setDraft(await api.draft(body));
      setStep("edit");
    });
  };

  const reset = () => {
    setDraft(null);
    setResults(null);
    setText("");
    setYear("");
    setManual({ title: "", year: "", runtime_min: "", overview: "" });
    setStep(me.tmdb ? "search" : "manual");
  };

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-3">
        <h1 className="font-display text-3xl font-semibold">Add a movie</h1>
        {step === "edit" && (
          <Button kind="ghost" onClick={reset}>
            Start over
          </Button>
        )}
      </header>

      {error && <Notice tone="error">{error}</Notice>}
      {busy && <Spinner label={`${busy}...`} />}

      {step === "search" && (
        <>
          <form onSubmit={search} className="grid grid-cols-[1fr_6rem] gap-2 sm:grid-cols-[1fr_7rem_auto]">
            <Field label="Title">
              <input autoFocus value={text} onChange={(e) => setText(e.target.value)} placeholder="e.g. The Thing" className={inputClass} />
            </Field>
            <Field label="Year">
              <input inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value.replace(/\D/g, "").slice(0, 4))} placeholder="1982" className={inputClass} />
            </Field>
            <Button kind="primary" type="submit" disabled={Boolean(busy) || !text.trim()} className="col-span-2 self-end sm:col-span-1">
              Search
            </Button>
          </form>

          {results && results.length === 0 && <Notice>TMDB found nothing. Check the spelling, or enter it by hand.</Notice>}
          {results && results.length > 0 && (
            <ul className="space-y-2">
              {results.map((c) => {
                const { main, sub } = titles(c);
                return (
                  <li key={c.tmdb_id}>
                    {c.on_list ? (
                      <a href={`#/movie/${c.on_list}`} className="flex gap-3 rounded-2xl border border-night-700 bg-night-800/40 p-3 opacity-70">
                        <Poster path={c.poster_path} title={main} size="w154" className="w-14 flex-none rounded-lg" />
                        <div className="min-w-0">
                          <p className="font-medium">
                            {main} {c.year && <span className="text-mist-400">({c.year})</span>}
                          </p>
                          <p className="text-sm text-coral-300">Already on the list</p>
                        </div>
                      </a>
                    ) : (
                      <button
                        type="button"
                        disabled={Boolean(busy)}
                        onClick={() => pick(c)}
                        className="flex w-full gap-3 rounded-2xl border border-night-700 bg-night-800/60 p-3 text-left transition hover:border-gold-400 disabled:opacity-50"
                      >
                        <Poster path={c.poster_path} title={main} size="w154" className="w-14 flex-none rounded-lg" />
                        <div className="min-w-0">
                          <p className="font-medium text-mist-100">
                            {main} {c.year && <span className="text-mist-400">({c.year})</span>}
                          </p>
                          {sub && <p className="text-sm text-mist-300">{sub}</p>}
                          {c.overview && <p className="mt-1 line-clamp-2 text-sm text-mist-400">{c.overview}</p>}
                        </div>
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          <button type="button" className="text-sm text-mist-400 underline underline-offset-4 hover:text-mist-100" onClick={() => setStep("manual")}>
            Not on TMDB? Enter it by hand
          </button>
        </>
      )}

      {step === "manual" && (
        <form onSubmit={fromManual} className="space-y-3">
          {!me.tmdb && <Notice>TMDB is not set up on this server, so movies are entered by hand.</Notice>}
          <Field label="Title">
            <input required autoFocus value={manual.title} onChange={(e) => setManual({ ...manual, title: e.target.value })} className={inputClass} />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Year">
              <input inputMode="numeric" value={manual.year} onChange={(e) => setManual({ ...manual, year: e.target.value.replace(/\D/g, "").slice(0, 4) })} className={inputClass} />
            </Field>
            <Field label="Minutes">
              <input inputMode="numeric" value={manual.runtime_min} onChange={(e) => setManual({ ...manual, runtime_min: e.target.value.replace(/\D/g, "").slice(0, 4) })} className={inputClass} />
            </Field>
          </div>
          <Field label="What is it about?" hint="Helps the tag suggestions.">
            <textarea rows={3} value={manual.overview} onChange={(e) => setManual({ ...manual, overview: e.target.value })} className={inputClass} />
          </Field>
          <div className="flex gap-2">
            <Button kind="primary" type="submit" disabled={Boolean(busy) || !manual.title.trim()}>
              Next
            </Button>
            {me.tmdb && <Button onClick={() => setStep("search")}>Back to search</Button>}
          </div>
        </form>
      )}

      {step === "edit" && draft && draft.already_on_list && (
        <Notice>
          This one is already on the list.{" "}
          <a className="text-gold-300 underline" href={`#/movie/${draft.already_on_list}`}>
            Open it
          </a>
        </Notice>
      )}
      {step === "edit" && draft && !draft.already_on_list && (
        <MovieEditor
          key={draft.tmdb_id ?? draft.title}
          initial={draft}
          vocab={vocab}
          onSaved={(movie) => {
            onSaved(movie);
            reset();
            window.location.hash = `#/movie/${movie.id}?added=1`;
          }}
          onCancel={reset}
          onDeleted={reset}
        />
      )}
    </div>
  );
}
