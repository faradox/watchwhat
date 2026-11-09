"""Tags and a blurb for one movie, suggested by an LLM (plan section 4).

One Messages call with a JSON-schema structured output, so the answer always
fits the fixed vocabularies. The model only judges (moods, attention,
intensity) and writes the blurb; every fact comes from TMDB or the person
adding the movie. The API key never leaves this module and is never logged;
only token counts and the estimated cost are.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from app import vocab

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60.0
MAX_TOKENS = 4000
MAX_BLURB = 320

# USD per million tokens (input, output), prompts up to 100k tokens.
PRICES = {"claude-haiku-5-5": (0.10, 0.50)}


class TaggerError(Exception):
    """A failed call. `kind` is a short code, safe to log and show."""

    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


@dataclass
class Tags:
    moods: list[str] = field(default_factory=list)
    attention: str | None = None
    violence: int | None = None
    scariness: int | None = None
    heaviness: int | None = None
    blurb: str | None = None
    # Set instead of tags when tagging was off or failed (a short code).
    error: str | None = None


def _describe(options: dict) -> str:
    return "\n".join(f"- {value}: {meaning}" for value, (_, meaning) in options.items())


def _scales() -> str:
    lines = []
    for key, (label, levels) in vocab.INTENSITY.items():
        steps = ", ".join(f"{i} {name.lower()}" for i, name in enumerate(levels))
        lines.append(f"- {key} ({label}): {steps}")
    return "\n".join(lines)


SYSTEM = f"""You tag movies for a couple's "what do we watch tonight?" list.
You get the facts about one movie. Judge it as a viewer would and answer with:

moods: 1 to {vocab.MAX_MOODS} values that best describe how the movie feels, the
most fitting first. Only these:
{_describe(vocab.MOODS)}

attention: how much focus it needs. One of:
{_describe(vocab.ATTENTION)}

intensity, each 0 to 3:
{_scales()}

blurb: one or two sentences, at most 40 words, that make clear what kind of
evening this movie is. No spoilers, no praise words like "masterpiece", do not
repeat the title, director or year.

Use what you know about the movie together with the facts given. If you do not
know the movie, judge from the facts alone and stay moderate."""


def output_schema() -> dict:
    level = {"type": "integer", "enum": list(vocab.LEVELS)}
    return {
        "type": "object",
        "properties": {
            "moods": {"type": "array", "items": {"type": "string", "enum": list(vocab.MOODS)}},
            "attention": {"type": "string", "enum": list(vocab.ATTENTION)},
            "violence": level,
            "scariness": level,
            "heaviness": level,
            "blurb": {"type": "string"},
        },
        "required": ["moods", "attention", "violence", "scariness", "heaviness", "blurb"],
        "additionalProperties": False,
    }


def facts_prompt(facts: dict) -> str:
    """The movie as the model sees it: only the fields that are known."""
    shown = {key: value for key, value in facts.items() if value not in (None, "", [])}
    return "The movie:\n" + json.dumps(shown, ensure_ascii=False, indent=1)


def clean(raw: dict) -> Tags:
    """Validate the model's answer again; anything off-vocabulary is dropped."""
    moods = []
    for mood in raw.get("moods") or []:
        if mood in vocab.MOODS and mood not in moods:
            moods.append(mood)
    attention = raw.get("attention")

    def level(key: str) -> int | None:
        value = raw.get(key)
        return value if isinstance(value, int) and value in vocab.LEVELS else None

    blurb = (raw.get("blurb") or "").strip()
    if len(blurb) > MAX_BLURB:
        blurb = blurb[: MAX_BLURB - 1].rsplit(" ", 1)[0] + "…"
    return Tags(
        moods=moods[: vocab.MAX_MOODS],
        attention=attention if attention in vocab.ATTENTION else None,
        violence=level("violence"),
        scariness=level("scariness"),
        heaviness=level("heaviness"),
        blurb=blurb or None,
    )


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES.get(model, max(PRICES.values()))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class Tagger:
    """Talks to the Anthropic API. Tests use a fake with the same `tag` method."""

    def __init__(self, api_key: str, model: str, effort: str = "low"):
        # Imported lazily so the rest of the app (and its tests) work without it.
        import anthropic

        self._anthropic = anthropic
        self.model = model
        self.effort = effort
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key, max_retries=2, timeout=TIMEOUT_SECONDS
        )

    async def close(self) -> None:
        await self._client.close()

    async def tag(self, facts: dict) -> Tags:
        anthropic = self._anthropic
        started = time.monotonic()
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM,
                messages=[{"role": "user", "content": facts_prompt(facts)}],
                output_config={
                    "effort": self.effort,
                    "format": {"type": "json_schema", "schema": output_schema()},
                },
            )
        except anthropic.AuthenticationError as exc:
            raise TaggerError("auth") from exc
        except (anthropic.PermissionDeniedError, anthropic.NotFoundError) as exc:
            raise TaggerError("permission") from exc
        except anthropic.RateLimitError as exc:
            raise TaggerError("rate_limited") from exc
        except anthropic.APITimeoutError as exc:
            raise TaggerError("timeout") from exc
        except anthropic.BadRequestError as exc:
            raise TaggerError("bad_request") from exc
        except anthropic.APIStatusError as exc:
            raise TaggerError(f"http_{exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise TaggerError("connection") from exc

        usage = response.usage
        log.info(
            "tagged in %d ms: %d in / %d out tokens, about $%.5f",
            int((time.monotonic() - started) * 1000),
            usage.input_tokens,
            usage.output_tokens,
            cost_usd(self.model, usage.input_tokens, usage.output_tokens),
        )
        if response.stop_reason != "end_turn":
            raise TaggerError(response.stop_reason or "no_answer")
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            raw = json.loads(text)
        except ValueError as exc:
            raise TaggerError("bad_json") from exc
        return clean(raw if isinstance(raw, dict) else {})
