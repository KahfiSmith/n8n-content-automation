#!/usr/bin/env python3
"""Helper OAuth TikTok untuk membuat auth URL dan menyimpan token lokal.

Token disimpan ke shared/config/tiktok_posting.json, bukan ke file contoh.
"""

from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import requests


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "shared" / "config" / "tiktok_posting.json"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
DEFAULT_SCOPES = "user.info.basic,video.upload,video.publish"


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Config harus object JSON: {path}")
    return payload


def save_config(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def require(config: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if not str(config.get(key, "")).strip()]
    if missing:
        raise SystemExit("Config TikTok belum lengkap. Field kosong: " + ", ".join(missing))


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def resolve_redirect_uri(args: argparse.Namespace, config: dict[str, Any]) -> str:
    redirect_uri = str(args.redirect_uri or config.get("redirect_uri") or "").strip()
    if not redirect_uri:
        raise SystemExit("redirect_uri kosong. Isi TIKTOK_REDIRECT_URI atau kirim --redirect-uri.")

    parsed = urlparse(redirect_uri)
    if parsed.scheme != "https":
        raise SystemExit("TikTok OAuth Web membutuhkan redirect_uri HTTPS yang terdaftar di Developer Portal.")
    return redirect_uri


def command_auth_url(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    require(config, ["client_key"])
    redirect_uri = resolve_redirect_uri(args, config)
    state = args.state or secrets.token_urlsafe(24)
    scopes = args.scopes or str(config.get("scope") or DEFAULT_SCOPES)
    query = urlencode(
        {
            "client_key": str(config["client_key"]),
            "response_type": "code",
            "scope": scopes,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    print_json(
        {
            "auth_url": f"{AUTH_URL}?{query}",
            "state": state,
            "scopes": scopes,
            "redirect_uri": redirect_uri,
            "note": "Pastikan redirect_uri sama persis dengan yang terdaftar di TikTok Developer Portal.",
        }
    )
    return 0


def command_exchange_code(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = load_config(config_path)
    require(config, ["client_key", "client_secret"])
    redirect_uri = resolve_redirect_uri(args, config)
    response = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
        data={
            "client_key": str(config["client_key"]),
            "client_secret": str(config["client_secret"]),
            "code": args.code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=120,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise SystemExit(
            f"Token exchange tidak mengembalikan JSON valid. status={response.status_code} body={response.text[:400]}"
        ) from exc

    if response.status_code >= 400 or payload.get("error"):
        raise SystemExit(
            "Token exchange gagal: "
            + str(payload.get("error_description") or payload.get("message") or response.text[:300])
        )

    config.update(
        {
            "access_token": str(payload.get("access_token") or "").strip(),
            "refresh_token": str(payload.get("refresh_token") or "").strip(),
            "open_id": str(payload.get("open_id") or "").strip(),
            "scope": str(payload.get("scope") or "").strip(),
            "token_type": str(payload.get("token_type") or "Bearer").strip(),
            "access_token_expires_in": payload.get("expires_in"),
            "refresh_token_expires_in": payload.get("refresh_expires_in"),
        }
    )
    save_config(config_path, config)
    print_json(
        {
            "status": "TIKTOK_TOKEN_SAVED",
            "config_path": str(config_path),
            "open_id": config.get("open_id"),
            "scope": config.get("scope"),
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helper OAuth TikTok lokal.")
    parser.add_argument(
        "--config",
        default=str(CONFIG_PATH),
        help="Path ke shared/config/tiktok_posting.json",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_url = subparsers.add_parser("auth-url", help="Buat URL authorization TikTok.")
    auth_url.add_argument("--redirect-uri", default=None)
    auth_url.add_argument("--scopes", default=DEFAULT_SCOPES)
    auth_url.add_argument("--state", default=None)
    auth_url.set_defaults(func=command_auth_url)

    exchange_code = subparsers.add_parser(
        "exchange-code",
        help="Tukar authorization code menjadi token dan simpan ke config lokal.",
    )
    exchange_code.add_argument("--code", required=True)
    exchange_code.add_argument("--redirect-uri", default=None)
    exchange_code.set_defaults(func=command_exchange_code)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
