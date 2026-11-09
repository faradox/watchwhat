// Small shared pieces: buttons, chips, segmented choices, fields, notices.

export function Button({ kind = "plain", className = "", ...props }) {
  const kinds = {
    primary: "bg-gold-400 text-night-950 hover:bg-gold-300 font-semibold",
    plain: "bg-night-700 text-mist-100 hover:bg-night-600",
    ghost: "text-mist-300 hover:text-mist-100 hover:bg-night-700",
    danger: "bg-night-700 text-coral-300 hover:bg-coral-400 hover:text-night-950",
  };
  return (
    <button
      type="button"
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${kinds[kind]} ${className}`}
      {...props}
    />
  );
}

export function LinkButton({ kind = "plain", className = "", ...props }) {
  const kinds = {
    primary: "bg-gold-400 text-night-950 hover:bg-gold-300 font-semibold",
    plain: "bg-night-700 text-mist-100 hover:bg-night-600",
  };
  return (
    <a
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm transition ${kinds[kind]} ${className}`}
      {...props}
    />
  );
}

export function Chip({ on, onClick, children, title }) {
  return (
    <button
      type="button"
      title={title}
      aria-pressed={on}
      onClick={onClick}
      className={`min-h-9 rounded-full border px-3 py-1 text-sm transition ${
        on
          ? "border-gold-400 bg-gold-400 text-night-950"
          : "border-night-600 bg-night-800 text-mist-300 hover:border-night-500 hover:text-mist-100"
      }`}
    >
      {children}
    </button>
  );
}

export function Tag({ children, tone = "plain" }) {
  const tones = {
    plain: "bg-night-700 text-mist-300",
    gold: "bg-gold-400/15 text-gold-300",
    coral: "bg-coral-400/15 text-coral-300",
  };
  return <span className={`rounded-full px-2.5 py-0.5 text-xs ${tones[tone]}`}>{children}</span>;
}

// One choice out of a few; `value` null means none chosen (when allowNone).
export function Segmented({ options, value, onChange, allowNone = false, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1 rounded-xl bg-night-800 p-1">
      {options.map((opt) => {
        const on = value === opt.value;
        return (
          <button
            key={String(opt.value)}
            type="button"
            role="radio"
            aria-checked={on}
            title={opt.hint}
            onClick={() => onChange(on && allowNone ? null : opt.value)}
            className={`min-h-9 flex-1 rounded-lg px-2.5 py-1 text-sm whitespace-nowrap transition ${
              on ? "bg-gold-400 font-medium text-night-950" : "text-mist-300 hover:bg-night-700"
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium tracking-wide text-mist-400 uppercase">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-mist-400">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "w-full rounded-xl border border-night-600 bg-night-800 px-3 py-2.5 text-mist-100 placeholder:text-night-500 focus:border-gold-400 focus:outline-none";

export function Notice({ tone = "plain", children }) {
  const tones = {
    plain: "border-night-600 bg-night-800 text-mist-300",
    error: "border-coral-400/40 bg-coral-400/10 text-coral-300",
    gold: "border-gold-400/40 bg-gold-400/10 text-gold-300",
  };
  return <div className={`rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>;
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-3 text-sm text-mist-400" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-night-600 border-t-gold-400" />
      {label}
    </div>
  );
}

export function Section({ title, children, right }) {
  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-xs font-medium tracking-wide text-mist-400 uppercase">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}
