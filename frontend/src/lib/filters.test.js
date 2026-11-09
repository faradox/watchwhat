import { describe, expect, it } from "vitest";
import {
  EMPTY_FILTERS,
  activeCount,
  filtersFromQuery,
  filtersToQuery,
  matches,
  minutesUntil,
  shuffle,
} from "./filters.js";

const movie = (over = {}) => ({
  id: 1,
  title: "Paddington 2",
  year: 2017,
  runtime_min: 104,
  original_language: "en",
  genres: ["Comedy", "Family"],
  moods: ["feel-good", "funny"],
  attention: "brain-off",
  violence: 0,
  scariness: 0,
  heaviness: 0,
  priority: false,
  ...over,
});

const f = (over = {}) => ({ ...EMPTY_FILTERS, ...over });
const evening = new Date(2026, 10, 9, 20, 0);

describe("matches", () => {
  it("lets everything through without filters", () => {
    expect(matches(movie(), f())).toBe(true);
  });

  it("ORs within a group and ANDs across groups", () => {
    expect(matches(movie(), f({ moods: ["dark", "funny"] }))).toBe(true);
    expect(matches(movie(), f({ moods: ["dark"] }))).toBe(false);
    expect(matches(movie(), f({ moods: ["funny"], genres: ["Horror"] }))).toBe(false);
  });

  it("filters by decade", () => {
    expect(matches(movie({ year: 1985 }), f({ decades: [1980, 1990] }))).toBe(true);
    expect(matches(movie({ year: 2001 }), f({ decades: [1980, 1990] }))).toBe(false);
    expect(matches(movie({ year: null }), f({ decades: [1980] }))).toBe(false);
  });

  it("keeps untagged movies under 'at most' limits only", () => {
    expect(matches(movie({ violence: null }), f({ maxViolence: 0 }))).toBe(true);
    expect(matches(movie({ violence: 2 }), f({ maxViolence: 1 }))).toBe(false);
    expect(matches(movie({ attention: null }), f({ attention: ["brain-off"] }))).toBe(false);
  });

  it("filters by language", () => {
    const samurai = movie({ original_language: "ja" });
    expect(matches(samurai, f({ lang: "en" }))).toBe(false);
    expect(matches(samurai, f({ lang: "other" }))).toBe(true);
    expect(matches(movie(), f({ lang: "other" }))).toBe(false);
  });

  it("fits a time budget", () => {
    expect(matches(movie({ runtime_min: 150 }), f({ time: { max: 120 } }))).toBe(false);
    expect(matches(movie({ runtime_min: 95 }), f({ time: { max: 120 } }))).toBe(true);
    expect(matches(movie({ runtime_min: null }), f({ time: { max: 90 } }))).toBe(true);
    // 20:00 until 22:00 is 120 minutes, minus 10 slack.
    const ctx = { now: evening };
    expect(matches(movie({ runtime_min: 110 }), f({ time: { until: "22:00" } }), ctx)).toBe(true);
    expect(matches(movie({ runtime_min: 111 }), f({ time: { until: "22:00" } }), ctx)).toBe(false);
  });

  it("never suggests hidden movies", () => {
    expect(matches(movie({ never_suggest: true }), f())).toBe(false);
  });

  it("applies the seen filter only when logged in", () => {
    const seenByFelix = movie({ seen_by: ["felix"] });
    const loggedIn = { loggedIn: true };
    expect(matches(seenByFelix, f(), loggedIn)).toBe(false);
    expect(matches(seenByFelix, f({ seen: "any" }), loggedIn)).toBe(true);
    expect(matches(seenByFelix, f({ seen: "sam" }), loggedIn)).toBe(true);
    expect(matches(seenByFelix, f({ seen: "felix" }), loggedIn)).toBe(false);
    expect(matches(movie({ seen_by: [] }), f(), loggedIn)).toBe(true);
    // Public movies carry no seen_by; the default must not hide anything.
    expect(matches(movie(), f(), loggedIn)).toBe(true);
    expect(matches(seenByFelix, f(), { loggedIn: false })).toBe(true);
  });
});

describe("minutesUntil", () => {
  it("counts to later today, minus slack", () => {
    expect(minutesUntil("23:30", evening)).toBe(200);
  });
  it("rolls over to tomorrow", () => {
    expect(minutesUntil("01:00", new Date(2026, 10, 9, 23, 0))).toBe(110);
  });
  it("rejects nonsense", () => {
    expect(minutesUntil("late", evening)).toBe(null);
  });
});

describe("URL form", () => {
  it("round-trips", () => {
    const filters = f({
      genres: ["Science Fiction", "Comedy"],
      moods: ["funny"],
      attention: ["brain-off"],
      decades: [1980, 1990],
      maxViolence: 1,
      maxScariness: 0,
      lang: "other",
      time: { until: "23:00" },
      seen: "sam",
    });
    expect(filtersFromQuery(filtersToQuery(filters))).toEqual(filters);
    const short = f({ time: { max: 100 } });
    expect(filtersFromQuery(filtersToQuery(short))).toEqual(short);
  });

  it("is empty for no filters", () => {
    expect(filtersToQuery(f())).toBe("");
    expect(filtersFromQuery("")).toEqual(f());
  });

  it("ignores garbage", () => {
    expect(filtersFromQuery("v=9&d=1985,x&l=fr&t=-4")).toEqual(f());
  });

  it("counts active filters", () => {
    expect(activeCount(f())).toBe(0);
    expect(activeCount(f({ moods: ["funny"], maxViolence: 0, time: { max: 90 } }))).toBe(3);
  });
});

describe("shuffle", () => {
  const many = Array.from({ length: 40 }, (_, i) => movie({ id: i, priority: i < 4 }));

  it("is stable for one seed and keeps every movie", () => {
    const a = shuffle(many, 42).map((m) => m.id);
    expect(shuffle(many, 42).map((m) => m.id)).toEqual(a);
    expect([...a].sort((x, y) => x - y)).toEqual(many.map((m) => m.id));
    expect(shuffle(many, 43).map((m) => m.id)).not.toEqual(a);
  });

  it("brings priority movies up more often", () => {
    let early = 0;
    for (let seed = 1; seed <= 300; seed++) {
      early += shuffle(many, seed)
        .slice(0, 10)
        .filter((m) => m.priority).length;
    }
    // Unweighted, 4 of 40 in the first 10 would average 1 per shuffle.
    expect(early / 300).toBeGreaterThan(1.6);
  });
});
