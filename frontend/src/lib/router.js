// Hash routes: #/ (tonight, filters in the query: #/?m=funny&d=1980),
// #/library, #/add, #/movie/12, #/movie/12/edit.
import { useEffect, useState } from "react";

export function parse(hash) {
  const [path, query = ""] = hash.replace(/^#/, "").split("?");
  const parts = path.split("/").filter(Boolean);
  return { page: parts[0] || "tonight", id: parts[1] ? Number(parts[1]) : null, sub: parts[2] || null, query };
}

export function useRoute() {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const onChange = () => {
      const next = parse(window.location.hash);
      setRoute((prev) => {
        // Filter changes on the same page keep the scroll position.
        if (prev.page !== next.page || prev.id !== next.id || prev.sub !== next.sub) window.scrollTo(0, 0);
        return next;
      });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export const go = (path) => {
  window.location.hash = path;
};

// Change the query without adding a history entry for every tap on a chip.
export function replaceQuery(path, query) {
  const hash = `#${path}${query ? `?${query}` : ""}`;
  if (window.location.hash !== hash) {
    window.history.replaceState(null, "", hash);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  }
}
