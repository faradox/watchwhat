import { useState } from "react";
import { EMPTY_FILTERS, activeCount, minutesUntil } from "../lib/filters.js";
import { INTENSITY_FIELDS } from "../lib/vocab.js";
import { Button, Chip, Section, Segmented, inputClass } from "./ui.jsx";

const TIME_PRESETS = [
  { value: 90, label: "≤ 1½h" },
  { value: 120, label: "≤ 2h" },
  { value: 150, label: "≤ 2½h" },
];

function toggled(list, value) {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}

export default function FilterPanel({ filters, onChange, vocab, me, decades, genres }) {
  const active = activeCount(filters);
  const [open, setOpen] = useState(active > 0);
  const set = (patch) => onChange({ ...filters, ...patch });
  const timeMode = filters.time?.until ? "until" : (filters.time?.max ?? null);
  const untilMinutes = filters.time?.until ? minutesUntil(filters.time.until) : null;

  return (
    <div className="rounded-3xl border border-night-700 bg-night-800/60 p-4 sm:p-5">
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5" aria-label="Mood">
          {vocab.moods.map((m) => (
            <Chip key={m.value} on={filters.moods.includes(m.value)} title={m.hint} onClick={() => set({ moods: toggled(filters.moods, m.value) })}>
              {m.label}
            </Chip>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Segmented
            label="Time"
            allowNone
            value={timeMode}
            onChange={(value) =>
              set({ time: value === null ? null : value === "until" ? { until: defaultUntil() } : { max: value } })
            }
            options={[...TIME_PRESETS, { value: "until", label: "Until…", hint: "Fits before a time tonight" }]}
          />
          {filters.time?.until && (
            <span className="flex items-center gap-2 text-sm text-mist-300">
              <input
                type="time"
                aria-label="Done by"
                value={filters.time.until}
                onChange={(e) => e.target.value && set({ time: { until: e.target.value } })}
                className={`${inputClass} w-auto! py-1.5`}
              />
              {untilMinutes != null && <span className="text-mist-400">{untilMinutes} min</span>}
            </span>
          )}
        </div>

        {me && (
          <label className="flex flex-wrap items-center gap-2 text-sm text-mist-300">
            <span className="text-xs font-medium tracking-wide text-mist-400 uppercase">Seen</span>
            <select value={filters.seen} onChange={(e) => set({ seen: e.target.value })} className={`${inputClass} w-auto! py-1.5`}>
              <option value="neither">{me.household.length > 1 ? "Neither of us has seen it" : "Not seen yet"}</option>
              {me.household.length > 1 &&
                me.household.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.display_name} hasn't seen it
                  </option>
                ))}
              <option value="any">Include seen movies</option>
            </select>
          </label>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Button kind="ghost" className="min-h-9 px-3" aria-expanded={open} onClick={() => setOpen(!open)}>
            {open ? "Fewer options" : "More options"}
            {active > 0 && <span className="rounded-full bg-gold-400 px-2 text-xs font-semibold text-night-950">{active}</span>}
          </Button>
          {(active > 0 || filters.seen !== EMPTY_FILTERS.seen) && (
            <Button kind="ghost" className="min-h-9 px-3" onClick={() => onChange({ ...EMPTY_FILTERS })}>
              Clear all
            </Button>
          )}
        </div>
      </div>

      {open && (
        <div className="mt-4 space-y-5 border-t border-night-700 pt-4">
          {decades.length > 0 && (
            <Section title="Decade">
              <div className="flex flex-wrap gap-1.5">
                {decades.map((d) => (
                  <Chip key={d} on={filters.decades.includes(d)} onClick={() => set({ decades: toggled(filters.decades, d) })}>
                    {d}s
                  </Chip>
                ))}
              </div>
            </Section>
          )}

          <Section title="Attention">
            <div className="flex flex-wrap gap-1.5">
              {vocab.attention.map((a) => (
                <Chip key={a.value} title={a.hint} on={filters.attention.includes(a.value)} onClick={() => set({ attention: toggled(filters.attention, a.value) })}>
                  {a.label}
                </Chip>
              ))}
            </div>
          </Section>

          {genres.length > 0 && (
            <Section title="Genre">
              <div className="flex flex-wrap gap-1.5">
                {genres.map((g) => (
                  <Chip key={g} on={filters.genres.includes(g)} onClick={() => set({ genres: toggled(filters.genres, g) })}>
                    {g}
                  </Chip>
                ))}
              </div>
            </Section>
          )}

          <Section title="At most">
            <div className="space-y-2">
              {vocab.intensity.map((scale) => {
                const key = INTENSITY_FIELDS[scale.key];
                return (
                  <div key={scale.key} className="grid items-center gap-1 sm:grid-cols-[7rem_1fr]">
                    <span className="text-sm text-mist-300">{scale.label}</span>
                    <Segmented
                      label={`Most ${scale.label.toLowerCase()}`}
                      allowNone
                      value={filters[key]}
                      onChange={(value) => set({ [key]: value })}
                      // The top level is "anything", which is no filter at all.
                      options={scale.levels.slice(0, -1).map((name, level) => ({ value: level, label: name }))}
                    />
                  </div>
                );
              })}
            </div>
          </Section>

          <Section title="Language">
            <Segmented
              label="Language"
              value={filters.lang}
              onChange={(lang) => set({ lang })}
              options={[
                { value: "any", label: "Any" },
                { value: "en", label: "English" },
                { value: "other", label: "Not English" },
              ]}
            />
          </Section>
        </div>
      )}
    </div>
  );
}

// "Until..." starts at 23:00; after 20:00, at two and a half hours from now.
function defaultUntil() {
  const now = new Date();
  const later = new Date(now.getTime() + 150 * 60000);
  if (now.getHours() < 20) return "23:00";
  return `${String(later.getHours()).padStart(2, "0")}:${String(later.getMinutes() - (later.getMinutes() % 15)).padStart(2, "0")}`;
}
