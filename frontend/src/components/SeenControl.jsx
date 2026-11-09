import { Chip } from "./ui.jsx";

// Who has seen it: one chip per person, plus "Both" for movies watched together.
export default function SeenControl({ seenBy, household, onChange, busy }) {
  const names = household.map((p) => p.name);
  const all = names.length > 1 && names.every((n) => seenBy.includes(n));
  const toggle = (name) =>
    onChange(seenBy.includes(name) ? seenBy.filter((n) => n !== name) : [...seenBy, name]);
  return (
    <div className={`flex flex-wrap items-center gap-2 ${busy ? "opacity-60" : ""}`}>
      <span className="text-xs font-medium tracking-wide text-mist-400 uppercase">Seen</span>
      {household.map((person) => {
        const on = seenBy.includes(person.name);
        return (
          <Chip key={person.name} on={on} onClick={() => toggle(person.name)}>
            {on ? "✓ " : ""}
            {person.display_name}
          </Chip>
        );
      })}
      {names.length > 1 && (
        <Chip on={all} onClick={() => onChange(all ? [] : names)} title="Watched it together">
          {all ? "✓ Both" : "Both"}
        </Chip>
      )}
    </div>
  );
}
