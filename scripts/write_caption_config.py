#!/usr/bin/env python3
"""Sync OpenAI caption settings from .env into shared/config/caption_ai.json."""

from __future__ import annotations

import json
from pathlib import Path

from env_utils import load_env

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
OUTPUT_PATH = ROOT / "shared" / "config" / "caption_ai.json"


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit(f".env tidak ditemukan di {ENV_PATH}")

    env = load_env(ENV_PATH)
    payload = {
        "openai_api_key": env.get("OPENAI_API_KEY", ""),
        "openai_caption_model": env.get("OPENAI_CAPTION_MODEL", "gpt-5.4-mini"),
        "openai_caption_language": env.get("OPENAI_CAPTION_LANGUAGE", "id"),
        "openai_caption_brand_voice": env.get(
            "OPENAI_CAPTION_BRAND_VOICE",
            "ringkas, tajam, natural, tidak clickbait murahan",
        ),
        "openai_caption_max_hashtags": int(env.get("OPENAI_CAPTION_MAX_HASHTAGS", "3") or "3"),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
