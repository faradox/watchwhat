"""The fixed tag vocabularies (plan section 3).

The single source for the backend's validation, the LLM's output schema and
the frontend's labels (served by GET /api/vocab). Adding a value here needs no
migration; renaming or removing one needs a data migration for stored movies.
"""

# TMDB's movie genres, in their English names.
GENRES = (
    "Action",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Music",
    "Mystery",
    "Romance",
    "Science Fiction",
    "TV Movie",
    "Thriller",
    "War",
    "Western",
)

# value -> (label, what it means; the LLM reads the meaning too)
MOODS = {
    "feel-good": ("Feel-good", "leaves you happier than before, warm and uplifting"),
    "funny": ("Funny", "made to make you laugh"),
    "cozy": ("Cozy", "gentle, comforting, low stakes"),
    "romantic": ("Romantic", "a love story is at its heart"),
    "tense": ("Tense", "suspense, edge of the seat"),
    "dark": ("Dark", "bleak, cynical or morally grim"),
    "mind-bending": ("Mind-bending", "twists, puzzles, reality in question"),
    "tearjerker": ("Tearjerker", "likely to make you cry"),
    "epic": ("Epic", "grand scale, spectacle, sweeping story"),
    "weird": ("Weird", "strange, surreal, off-beat"),
}
MAX_MOODS = 3

ATTENTION = {
    "brain-off": ("Brain off", "easy to follow while tired or chatting"),
    "normal": ("Normal", "an ordinary movie that wants you to follow along"),
    "full-focus": ("Full focus", "dense, slow or complex; miss a scene and you are lost"),
}

# Scale name -> (label, level labels 0..3)
INTENSITY = {
    "violence": ("Violence", ("None", "Mild", "Strong", "Graphic")),
    "scariness": ("Scariness", ("Not scary", "A little", "Scary", "Terrifying")),
    "heaviness": ("Heaviness", ("Light", "Some weight", "Heavy", "Devastating")),
}
LEVELS = (0, 1, 2, 3)


def as_json() -> dict:
    return {
        "genres": list(GENRES),
        "moods": [{"value": k, "label": v[0], "hint": v[1]} for k, v in MOODS.items()],
        "max_moods": MAX_MOODS,
        "attention": [
            {"value": k, "label": v[0], "hint": v[1]} for k, v in ATTENTION.items()
        ],
        "intensity": [
            {"key": k, "label": v[0], "levels": list(v[1])} for k, v in INTENSITY.items()
        ],
    }
