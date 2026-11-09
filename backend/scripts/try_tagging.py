"""PAID: tag one movie with the real model and print what it says.

    python -m scripts.try_tagging 348            # a TMDB id (needs TMDB_TOKEN)
    python -m scripts.try_tagging "Alien" 1979   # a title, facts typed by you

Uses ANTHROPIC_API_KEY and LLM_MODEL from the environment. One call costs a
fraction of a cent with Haiku. It asks before it calls; there is no flag to
skip that. Nothing is saved.
"""

import asyncio
import json
import sys

from app.tagger import Tagger
from app.tagging import FACT_FIELDS
from app.tmdb import TMDB
from config import Settings


async def main(args: list[str]) -> int:
    cfg = Settings()
    if not cfg.anthropic_api_key:
        print("ANTHROPIC_API_KEY is not set.")
        return 1
    if args and args[0].isdigit() and len(args) == 1:
        if not cfg.tmdb_token:
            print("TMDB_TOKEN is not set; pass a title instead.")
            return 1
        tmdb = TMDB(cfg.tmdb_token)
        try:
            facts = (await tmdb.facts(int(args[0]))).__dict__
        finally:
            await tmdb.close()
    elif args:
        facts = {"title": args[0], "year": int(args[1]) if len(args) > 1 else None}
    else:
        print(__doc__)
        return 1
    shown = {key: facts.get(key) for key in FACT_FIELDS}
    print(json.dumps(shown, ensure_ascii=False, indent=1))
    answer = input(f"\nSend this to {cfg.llm_model} (costs well under a cent)? Type yes: ")
    if answer.strip().lower() != "yes":
        print("Not sent.")
        return 1
    tagger = Tagger(cfg.anthropic_api_key, cfg.llm_model, cfg.llm_effort)
    try:
        tags = await tagger.tag(shown)
    finally:
        await tagger.close()
    print(json.dumps(tags.__dict__, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
