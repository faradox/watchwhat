// Links and labels derived from a movie.

const IMAGE_BASE = "https://image.tmdb.org/t/p";

export function posterUrl(path, size = "w500") {
  return path ? `${IMAGE_BASE}/${size}${path}` : null;
}

export function trailerUrl(movie) {
  if (movie.trailer_youtube_key) {
    return `https://www.youtube.com/watch?v=${encodeURIComponent(movie.trailer_youtube_key)}`;
  }
  const query = [movie.original_title || movie.title, movie.year, "trailer"].filter(Boolean).join(" ");
  return `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
}

export function imdbUrl(movie) {
  return movie.imdb_id ? `https://www.imdb.com/title/${encodeURIComponent(movie.imdb_id)}/` : null;
}

export function tmdbUrl(movie) {
  return movie.tmdb_id ? `https://www.themoviedb.org/movie/${movie.tmdb_id}` : null;
}

// Main title in the original language; the English one underneath when it
// differs (and always when the original is in a script we may not read).
export function titles(movie) {
  const original = movie.original_title || movie.title;
  const english = movie.title && movie.title !== original ? movie.title : null;
  return { main: original, sub: english };
}

export function runtimeLabel(minutes) {
  if (!minutes) return null;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h}h${m ? ` ${String(m).padStart(2, "0")}m` : ""}` : `${m}m`;
}

const LANGUAGES = typeof Intl !== "undefined" && Intl.DisplayNames ? new Intl.DisplayNames(["en"], { type: "language" }) : null;

export function languageLabel(code) {
  if (!code) return null;
  try {
    return LANGUAGES?.of(code) || code;
  } catch {
    return code;
  }
}
