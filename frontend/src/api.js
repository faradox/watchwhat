// API client. Relative URLs: the host's proxy (prod) or the Vite proxy (dev) routes /api.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    credentials: "same-origin",
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      // Not JSON: the login proxy's own answer (the session ran out).
      if (res.status === 401) detail = "Your login ran out. Log in again.";
    }
    if (Array.isArray(detail)) detail = detail.map((d) => `${d.loc?.slice(-1)[0] ?? ""}: ${d.msg}`).join("; ");
    throw new ApiError(typeof detail === "string" ? detail : `HTTP ${res.status}`, res.status);
  }
  return res.status === 204 ? null : res.json();
}

const q = (params) => {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ""));
  return `?${new URLSearchParams(clean)}`;
};

export const LOGIN_URL = "/api/private/login";

export const api = {
  vocab: () => request("GET", "/vocab"),
  publicMovies: () => request("GET", "/movies"),

  // null when nobody is logged in (or the login is not for this household).
  me: async () => {
    try {
      return await request("GET", "/private/me");
    } catch (err) {
      if (err.status === 401 || err.status === 403) return null;
      throw err;
    }
  },
  movies: () => request("GET", "/private/movies"),
  movie: (id) => request("GET", `/private/movies/${id}`),
  createMovie: (body) => request("POST", "/private/movies", body),
  updateMovie: (id, body) => request("PUT", `/private/movies/${id}`, body),
  // { priority?, never_suggest? }
  setFlags: (id, flags) => request("PATCH", `/private/movies/${id}`, flags),
  deleteMovie: (id) => request("DELETE", `/private/movies/${id}`),
  setSeen: (id, users) => request("PUT", `/private/movies/${id}/seen`, { users }),
  retag: (id) => request("POST", `/private/movies/${id}/retag`),

  search: (text, year) => request("GET", `/private/tmdb/search${q({ q: text, year })}`),
  // { tmdb_id } or { title, year?, runtime_min?, overview?, original_language? }
  draft: (body) => request("POST", "/private/drafts", body),
};
