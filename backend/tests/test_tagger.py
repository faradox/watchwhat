import asyncio
import json
from types import SimpleNamespace

import pytest

from app import tagger, vocab
from app.tagger import Tagger, TaggerError, clean, facts_prompt, output_schema


def test_clean_keeps_only_the_vocabulary():
    tags = clean(
        {
            "moods": ["tense", "sleepy", "tense", "dark", "weird", "epic"],
            "attention": "half",
            "violence": 2,
            "scariness": 7,
            "heaviness": "1",
            "blurb": "  Fine.  ",
        }
    )
    assert tags.moods == ["tense", "dark", "weird"]
    assert tags.attention is None
    assert tags.violence == 2
    assert tags.scariness is None
    assert tags.heaviness is None
    assert tags.blurb == "Fine."


def test_clean_shortens_long_blurbs_at_a_word():
    tags = clean({"blurb": "word " * 200})
    assert len(tags.blurb) <= tagger.MAX_BLURB
    assert tags.blurb.endswith("word…")


def test_schema_matches_the_vocabulary():
    schema = output_schema()
    assert schema["properties"]["moods"]["items"]["enum"] == list(vocab.MOODS)
    assert schema["properties"]["attention"]["enum"] == list(vocab.ATTENTION)
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


def test_system_prompt_names_every_value():
    for value in [*vocab.MOODS, *vocab.ATTENTION, *vocab.INTENSITY]:
        assert value in tagger.SYSTEM


def test_facts_prompt_leaves_out_unknowns():
    text = facts_prompt({"title": "Alien", "year": 1979, "overview": None, "cast": []})
    assert json.loads(text.split("\n", 1)[1]) == {"title": "Alien", "year": 1979}


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def make_tagger(response) -> tuple[Tagger, FakeMessages]:
    """A real Tagger around a fake SDK client (creating a real one fails the test)."""
    import anthropic

    instance = object.__new__(Tagger)
    instance._anthropic = anthropic
    instance.model = "claude-haiku-5-5"
    instance.effort = "low"
    messages = FakeMessages(response)
    instance._client = SimpleNamespace(messages=messages)
    return instance, messages


def response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=900, output_tokens=120),
    )


def test_tag_sends_the_schema_and_reads_the_answer():
    answer = {
        "moods": ["funny"],
        "attention": "brain-off",
        "violence": 0,
        "scariness": 0,
        "heaviness": 0,
        "blurb": "Silly and sweet.",
    }
    instance, messages = make_tagger(response(json.dumps(answer)))
    tags = asyncio.run(instance.tag({"title": "Paddington 2"}))
    assert tags.moods == ["funny"]
    assert tags.blurb == "Silly and sweet."
    [call] = messages.calls
    assert call["model"] == "claude-haiku-5-5"
    assert call["output_config"]["effort"] == "low"
    assert call["output_config"]["format"] == {"type": "json_schema", "schema": output_schema()}
    assert "Paddington 2" in call["messages"][0]["content"]
    assert "temperature" not in call and "thinking" not in call


@pytest.mark.parametrize(
    "reply, kind",
    [
        (response("{}", stop_reason="max_tokens"), "max_tokens"),
        (response("{}", stop_reason="refusal"), "refusal"),
        (response("not json"), "bad_json"),
    ],
)
def test_tag_failures(reply, kind):
    instance, _ = make_tagger(reply)
    with pytest.raises(TaggerError) as info:
        asyncio.run(instance.tag({"title": "X"}))
    assert info.value.kind == kind


def test_cost_estimate():
    assert tagger.cost_usd("claude-haiku-5-5", 1_000_000, 1_000_000) == pytest.approx(0.60)
