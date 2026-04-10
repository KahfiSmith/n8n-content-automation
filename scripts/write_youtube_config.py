#!/usr/bin/env python3
"""Sync YouTube OAuth settings from .env into shared/config/youtube_oauth.json."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
OUTPUT_PATH = ROOT / "shared" / "config" / "youtube_oauth.json"


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
        "client_id": env.get("YOUTUBE_CLIENT_ID", ""),
        "client_secret": env.get("YOUTUBE_CLIENT_SECRET", ""),
        "refresh_token": env.get("YOUTUBE_REFRESH_TOKEN", ""),
        "privacy_status": env.get("YOUTUBE_PRIVACY_STATUS", "private"),
        "category_id": env.get("YOUTUBE_CATEGORY_ID", "22"),
        "notify_subscribers": to_bool(env.get("YOUTUBE_NOTIFY_SUBSCRIBERS"), False),
        "self_declared_made_for_kids": to_bool(
            env.get("YOUTUBE_SELF_DECLARED_MADE_FOR_KIDS"),
            False,
        ),
        "allow_publish_without_approval": to_bool(
            env.get("YOUTUBE_ALLOW_PUBLISH_WITHOUT_APPROVAL"),
            True,
        ),
        "title_suffix": env.get("YOUTUBE_TITLE_SUFFIX", ""),
        "description_footer": env.get("YOUTUBE_DESCRIPTION_FOOTER", ""),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
