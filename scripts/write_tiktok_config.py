#!/usr/bin/env python3
"""Sync TikTok Content Posting settings from .env into shared/config/tiktok_posting.json."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
OUTPUT_PATH = ROOT / "shared" / "config" / "tiktok_posting.json"


def load_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def to_bool(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit(f".env tidak ditemukan di {ENV_PATH}")

    env = load_env(ENV_PATH)
    payload = {
        "client_key": env.get("TIKTOK_CLIENT_KEY", ""),
        "client_secret": env.get("TIKTOK_CLIENT_SECRET", ""),
        "access_token": env.get("TIKTOK_ACCESS_TOKEN", ""),
        "refresh_token": env.get("TIKTOK_REFRESH_TOKEN", ""),
        "open_id": env.get("TIKTOK_OPEN_ID", ""),
        "scope": env.get("TIKTOK_SCOPE", ""),
        "redirect_uri": env.get("TIKTOK_REDIRECT_URI", ""),
        "post_mode": env.get("TIKTOK_POST_MODE", "UPLOAD"),
        "source": env.get("TIKTOK_SOURCE", "FILE_UPLOAD"),
        "privacy_level": env.get("TIKTOK_PRIVACY_LEVEL", "SELF_ONLY"),
        "disable_comment": to_bool(env.get("TIKTOK_DISABLE_COMMENT"), False),
        "disable_duet": to_bool(env.get("TIKTOK_DISABLE_DUET"), False),
        "disable_stitch": to_bool(env.get("TIKTOK_DISABLE_STITCH"), False),
        "brand_content_toggle": to_bool(env.get("TIKTOK_BRAND_CONTENT_TOGGLE"), False),
        "brand_organic_toggle": to_bool(env.get("TIKTOK_BRAND_ORGANIC_TOGGLE"), False),
        "is_aigc": to_bool(env.get("TIKTOK_IS_AIGC"), False),
        "title_suffix": env.get("TIKTOK_TITLE_SUFFIX", ""),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
