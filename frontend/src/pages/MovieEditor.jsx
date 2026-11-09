import { useState } from "react";
import { api } from "../api.js";
import Poster from "../components/Poster.jsx";
import { Button, Chip, Field, Notice, Section, Segmented, Spinner, inputClass } from "../components/ui.jsx";
import { titles } from "../lib/links.js";

// What the editor sends back: everything the API's MovieFields accepts.
const FIELDS = [
  "tmdb_id", "imdb_id", "title", "original_title", "original_language", "year", "runtime_min",
  "genres", "keywords", "director", "cast", "overview", "poster_path", "trailer_youtube_key",
  "vote_average", "blurb", "moods", "attention", "violence", "scariness", "heaviness",
  "priority", "never_suggest", "verified",
];

export function toBody(movie) {
  const body = Object.fromEntries(FIELDS.map((key) => [key, movie[key] ?? null]));
  for (const key of ["genres", "keywords", "cast", "moods"]) body[key] = body[key] || [];
  for (const key of ["priority", "never_suggest"]) body[key] = Boolean(body[key]);
  body.verified = movie.verified !== false;
  return body;
}

const number = (value) => (value === "" ? null : Number(value));

// Edit a draft (new movie) or a saved movie. `onSaved(movie)` after saving.
export default function MovieEditor({ initial, vocab, onSaved, onDeleted, onCancel }) {
  const [movie, setMovie] = useState(() => toBody(initial));
  const [saving, setSaving] = useState(false);
  const [retagging, setRetagging] = useState(false);
  const [error, setError] = useState(null);
  const isNew = !initial.id;
  const set = (patch) => setMovie((m) => ({ ...m, ...patch }));
  const toggle = (key, value, max) => {
    const list = movie[key];
    if (list.includes(value)) return set({ [key]: list.filter((v) => v !== value) });
    if (max && list.length >= max) return;
    set({ [key]: [...list, value] });
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const saved = isNew ? await api.createMovie(movie) : await api.updateMovie(initial.id, movie);
      onSaved(saved);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  const retag = async () => {
    setRetagging(true);
    setError(null);
    try {
      // Suggestions from the saved facts; the edits above are kept.
      set(await api.retag(initial.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setRetagging(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${titles(initial).main}" from the list?`)) return;
    try {
      await api.deleteMovie(initial.id);
      onDeleted(initial);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form onSubmit={save} className="space-y-6">
      <div className="flex gap-4">
        <Poster path={movie.poster_path} title={movie.title} size="w342" className="w-24 flex-none rounded-xl sm:w-32" />
        <div className="min-w-0 flex-1 space-y-3">
          <Field label="Title (English)">
            <input required value={movie.title || ""} onChange={(e) => set({ title: e.target.value })} className={inputClass} />
          </Field>
          <Field label="Original title">
            <input value={movie.original_title || ""} onChange={(e) => set({ original_title: e.target.value })} className={inputClass} />
          </Field>
        </div>
      </div>

      {initial.tag_error && <Notice tone="gold">{initial.tag_error} Set the tags by hand.</Notice>}

      <div className="grid grid-cols-3 gap-3">
        <Field label="Year">
          <input inputMode="numeric" value={movie.year ?? ""} onChange={(e) => set({ year: number(e.target.value) })} className={inputClass} />
        </Field>
        <Field label="Minutes">
          <input inputMode="numeric" value={movie.runtime_min ?? ""} onChange={(e) => set({ runtime_min: number(e.target.value) })} className={inputClass} />
        </Field>
        <Field label="Language" hint="en, ja, fr...">
          <input value={movie.original_language || ""} onChange={(e) => set({ original_language: e.target.value })} className={inputClass} />
        </Field>
      </div>

      <Field label="Blurb" hint="One or two sentences: what kind of evening is this?">
        <textarea rows={3} value={movie.blurb || ""} onChange={(e) => set({ blurb: e.target.value })} className={inputClass} />
      </Field>

      <Section
        title={`Mood (up to ${vocab.max_moods})`}
        right={
          !isNew && (
            <Button kind="ghost" className="min-h-8 px-2 py-1 text-xs" onClick={retag} disabled={retagging}>
              {retagging ? "Asking..." : "Suggest tags again"}
            </Button>
          )
        }
      >
        <div className="flex flex-wrap gap-1.5">
          {vocab.moods.map((m) => (
            <Chip key={m.value} title={m.hint} on={movie.moods.includes(m.value)} onClick={() => toggle("moods", m.value, vocab.max_moods)}>
              {m.label}
            </Chip>
          ))}
        </div>
      </Section>

      <Section title="Attention">
        <Segmented label="Attention" allowNone value={movie.attention} onChange={(attention) => set({ attention })} options={vocab.attention} />
      </Section>

      <Section title="Intensity">
        <div className="space-y-2">
          {vocab.intensity.map((scale) => (
            <div key={scale.key} className="grid items-center gap-1 sm:grid-cols-[7rem_1fr]">
              <span className="text-sm text-mist-300">{scale.label}</span>
              <Segmented
                label={scale.label}
                allowNone
                value={movie[scale.key]}
                onChange={(value) => set({ [scale.key]: value })}
                options={scale.levels.map((name, level) => ({ value: level, label: name }))}
              />
            </div>
          ))}
        </div>
      </Section>

      <Section title="Genres">
        <div className="flex flex-wrap gap-1.5">
          {vocab.genres.map((g) => (
            <Chip key={g} on={movie.genres.includes(g)} onClick={() => toggle("genres", g)}>
              {g}
            </Chip>
          ))}
        </div>
      </Section>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Trailer" hint="A YouTube link or video id">
          <input value={movie.trailer_youtube_key || ""} onChange={(e) => set({ trailer_youtube_key: e.target.value })} className={inputClass} />
        </Field>
        <Field label="IMDb" hint="A link or tt... id">
          <input value={movie.imdb_id || ""} onChange={(e) => set({ imdb_id: e.target.value })} className={inputClass} />
        </Field>
        <Field label="Director">
          <input value={movie.director || ""} onChange={(e) => set({ director: e.target.value })} className={inputClass} />
        </Field>
      </div>

      <Field label="Plot" hint="From TMDB; shown when there is no blurb.">
        <textarea rows={4} value={movie.overview || ""} onChange={(e) => set({ overview: e.target.value })} className={inputClass} />
      </Field>

      <div className="space-y-2">
        <label className="flex items-center gap-3 text-sm text-mist-300">
          <input type="checkbox" checked={movie.priority} onChange={(e) => set({ priority: e.target.checked })} className="h-5 w-5 accent-gold-400" />
          Top of the list: we both really want to see this (comes up more often)
        </label>
        <label className="flex items-center gap-3 text-sm text-mist-300">
          <input type="checkbox" checked={movie.never_suggest} onChange={(e) => set({ never_suggest: e.target.checked })} className="h-5 w-5 accent-gold-400" />
          Never suggest (keep it in the list only)
        </label>
      </div>

      {error && <Notice tone="error">{error}</Notice>}

      <div className="sticky bottom-0 -mx-4 flex flex-wrap gap-2 border-t border-night-700 bg-night-900/95 px-4 py-3 backdrop-blur">
        <Button kind="primary" type="submit" disabled={saving} className="flex-1">
          {saving ? <Spinner label="Saving" /> : isNew ? "Save to the list" : "Save"}
        </Button>
        <Button onClick={onCancel}>Cancel</Button>
        {!isNew && (
          <Button kind="danger" onClick={remove}>
            Delete
          </Button>
        )}
      </div>
    </form>
  );
}
