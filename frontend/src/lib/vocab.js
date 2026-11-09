// Labels from GET /api/vocab.

export function labeler(vocab) {
  const moods = Object.fromEntries((vocab?.moods || []).map((m) => [m.value, m.label]));
  const attention = Object.fromEntries((vocab?.attention || []).map((a) => [a.value, a.label]));
  const intensity = Object.fromEntries((vocab?.intensity || []).map((s) => [s.key, s]));
  return {
    mood: (value) => moods[value] || value,
    attention: (value) => attention[value] || value,
    level: (key, value) => (value == null ? null : intensity[key]?.levels[value] ?? String(value)),
    scale: (key) => intensity[key]?.label || key,
  };
}

export const INTENSITY_FIELDS = { violence: "maxViolence", scariness: "maxScariness", heaviness: "maxHeaviness" };
