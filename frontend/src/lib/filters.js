// The recommender's filters: matching, the URL form, and the random order.
// Pure functions, unit tested in filters.test.js.
//
// Rules: values within one group are OR'ed, groups are AND'ed. A movie that
// lacks a value is left out by "pick from a list" filters (genre, mood,
// attention, decade, language) but kept by "at most" filters (intensity,
// time), so a missing tag never hides a movie you did not filter on.

export const SLACK_MINUTES = 10;

export const EMPTY_FILTERS = Object.freeze({
  genres: [],
  moods: [],
  attention: [],
  decades: [],
  maxViolence: null,
  maxScariness: null,
  maxHeaviness: null,
  lang: "any", // any | en | other
  time: null, // null | { max: minutes } | { until: "HH:MM" }
  seen: "neither", // logged in only: neither | any | <user name> (hasn't seen it)
});

const LIST_KEYS = { genres: "g", moods: "m", attention: "a", decades: "d" };
const MAX_KEYS = { maxViolence: "v", maxScariness: "s", maxHeaviness: "h" };

export function decadeOf(year) {
  return year ? Math.floor(year / 10) * 10 : null;
}

// Minutes from `now` until the clock shows `hhmm` (tomorrow if already past),
// minus the slack for snacks and finding the remote.
export function minutesUntil(hhmm, now = new Date()) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(hhmm || "");
  if (!match) return null;
  const target = new Date(now);
  target.setHours(Number(match[1]), Number(match[2]), 0, 0);
  if (target <= now) target.setDate(target.getDate() + 1);
  return Math.round((target - now) / 60000) - SLACK_MINUTES;
}

export function timeBudget(time, now = new Date()) {
  if (!time) return null;
  if (time.max) return time.max;
  if (time.until) return minutesUntil(time.until, now);
  return null;
}

export function matches(movie, filters, { loggedIn = false, now = new Date() } = {}) {
  const f = filters;
  if (movie.never_suggest) return false;
  const anyOf = (wanted, values) => wanted.length === 0 || values.some((v) => wanted.includes(v));
  if (!anyOf(f.genres, movie.genres || [])) return false;
  if (!anyOf(f.moods, movie.moods || [])) return false;
  if (!anyOf(f.attention, movie.attention ? [movie.attention] : [])) return false;
  if (!anyOf(f.decades, movie.year ? [decadeOf(movie.year)] : [])) return false;
  const atMost = (limit, value) => limit == null || value == null || value <= limit;
  if (!atMost(f.maxViolence, movie.violence)) return false;
  if (!atMost(f.maxScariness, movie.scariness)) return false;
  if (!atMost(f.maxHeaviness, movie.heaviness)) return false;
  if (f.lang === "en" && movie.original_language !== "en") return false;
  if (f.lang === "other" && (!movie.original_language || movie.original_language === "en")) return false;
  const budget = timeBudget(f.time, now);
  if (budget != null && movie.runtime_min != null && movie.runtime_min > budget) return false;
  if (loggedIn && Array.isArray(movie.seen_by)) {
    if (f.seen === "neither" && movie.seen_by.length > 0) return false;
    if (f.seen !== "neither" && f.seen !== "any" && movie.seen_by.includes(f.seen)) return false;
  }
  return true;
}

export function activeCount(filters) {
  const f = filters;
  return (
    Object.keys(LIST_KEYS).filter((k) => f[k].length).length +
    Object.keys(MAX_KEYS).filter((k) => f[k] != null).length +
    (f.lang !== "any" ? 1 : 0) +
    (f.time ? 1 : 0)
  );
}

// Filters <-> URL query, so a filtered view can be bookmarked or shared.
export function filtersToQuery(filters) {
  const params = new URLSearchParams();
  for (const [key, short] of Object.entries(LIST_KEYS)) {
    if (filters[key].length) params.set(short, filters[key].join(","));
  }
  for (const [key, short] of Object.entries(MAX_KEYS)) {
    if (filters[key] != null) params.set(short, String(filters[key]));
  }
  if (filters.lang !== "any") params.set("l", filters.lang);
  if (filters.time?.max) params.set("t", String(filters.time.max));
  if (filters.time?.until) params.set("t", `@${filters.time.until}`);
  if (filters.seen !== EMPTY_FILTERS.seen) params.set("seen", filters.seen);
  return params.toString();
}

export function filtersFromQuery(query) {
  const params = new URLSearchParams(query || "");
  const filters = { ...EMPTY_FILTERS };
  for (const [key, short] of Object.entries(LIST_KEYS)) {
    const raw = params.get(short);
    if (!raw) continue;
    const values = raw.split(",").filter(Boolean);
    filters[key] = key === "decades" ? values.map(Number).filter((n) => n % 10 === 0) : values;
  }
  for (const [key, short] of Object.entries(MAX_KEYS)) {
    const value = Number(params.get(short));
    if (params.has(short) && Number.isInteger(value) && value >= 0 && value <= 3) filters[key] = value;
  }
  const lang = params.get("l");
  if (lang === "en" || lang === "other") filters.lang = lang;
  const time = params.get("t");
  if (time?.startsWith("@") && minutesUntil(time.slice(1)) != null) {
    filters.time = { until: time.slice(1) };
  } else if (Number(time) > 0) {
    filters.time = { max: Number(time) };
  }
  if (params.get("seen")) filters.seen = params.get("seen");
  return filters;
}

// Deterministic random numbers, so one shuffle stays put across re-renders.
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const PRIORITY_WEIGHT = 3;

// Weighted random order (Efraimidis-Spirakis): priority movies weigh 3x, so
// they tend to come early, but every movie comes up eventually.
export function shuffle(movies, seed) {
  const random = mulberry32(seed);
  return movies
    .map((movie) => {
      const weight = movie.priority ? PRIORITY_WEIGHT : 1;
      return { movie, key: Math.pow(random() || Number.MIN_VALUE, 1 / weight) };
    })
    .sort((a, b) => b.key - a.key)
    .map((entry) => entry.movie);
}

export function newSeed() {
  return Math.floor(Math.random() * 2 ** 31);
}
