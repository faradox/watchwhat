import { useState } from "react";
import { posterUrl } from "../lib/links.js";

// A poster, or a quiet placeholder with the title for movies without one.
export default function Poster({ path, title, size = "w500", className = "" }) {
  const [failed, setFailed] = useState(false);
  const url = posterUrl(path, size);
  const small = size === "w92" || size === "w154";
  if (!url || failed) {
    return (
      <div
        className={`flex aspect-[2/3] items-center justify-center overflow-hidden bg-gradient-to-br from-night-700 to-night-800 text-center font-display text-mist-400 ${small ? "p-1" : "p-3"} ${className}`}
      >
        <span className={`line-clamp-4 break-words ${small ? "text-[10px] leading-tight" : "text-sm"}`}>{title}</span>
      </div>
    );
  }
  return (
    <img
      src={url}
      alt={`Poster: ${title}`}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`aspect-[2/3] bg-night-800 object-cover ${className}`}
    />
  );
}
