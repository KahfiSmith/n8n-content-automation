#!/usr/bin/env python3
"""Helper CLI untuk TikTok Content Posting API.

Mode yang didukung:
- UPLOAD: kirim video ke inbox/draft TikTok
- DIRECT_POST: post langsung ke profil TikTok

Script ini sengaja dipisahkan dari workflow aktif supaya TikTok bisa disiapkan
lebih dulu tanpa menambah titik gagal di MVP YouTube yang sudah berjalan.
"""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "shared" / "config" / "tiktok_posting.json"
API_BASE = "https://open.tiktokapis.com"
TOKEN_URL = f"{API_BASE}/v2/oauth/token/"
UPLOAD_CHUNK_SIZE = 10_000_000


class TikTokConfigError(RuntimeError):
    """Raised when the TikTok local config is invalid."""


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise TikTokConfigError(
            f"Config TikTok tidak ditemukan di {path}. Jalankan python3 scripts/write_tiktok_config.py dulu."
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TikTokConfigError("Isi config TikTok harus object JSON.")

    return payload


def ensure_required(config: dict[str, Any], keys: list[str]) -> None:
    missing = [key for key in keys if not str(config.get(key, "")).strip()]
    if missing:
        raise TikTokConfigError(
            "Config TikTok belum lengkap. Field kosong: " + ", ".join(missing)
        )


def save_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def refresh_access_token(config: dict[str, Any], path: Path) -> dict[str, Any]:
    ensure_required(config, ["client_key", "client_secret", "refresh_token"])
    response = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
        data={
            "client_key": str(config["client_key"]),
            "client_secret": str(config["client_secret"]),
            "grant_type": "refresh_token",
            "refresh_token": str(config["refresh_token"]),
        },
        timeout=120,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Refresh token TikTok tidak mengembalikan JSON valid. status={response.status_code} body={response.text[:400]}"
        ) from exc

    if response.status_code >= 400 or payload.get("error"):
        raise TikTokConfigError(
            "Refresh token TikTok gagal. "
            + str(payload.get("error_description") or payload.get("message") or response.text[:300])
        )

    config.update(
        {
            "access_token": str(payload.get("access_token") or "").strip(),
            "refresh_token": str(payload.get("refresh_token") or config.get("refresh_token") or "").strip(),
            "open_id": str(payload.get("open_id") or config.get("open_id") or "").strip(),
            "scope": str(payload.get("scope") or config.get("scope") or "").strip(),
            "token_type": str(payload.get("token_type") or "Bearer").strip(),
            "access_token_expires_in": payload.get("expires_in"),
            "refresh_token_expires_in": payload.get("refresh_expires_in"),
            "token_refreshed_at": utc_now_iso(),
        }
    )
    if not config["access_token"]:
        raise TikTokConfigError("Refresh token TikTok berhasil dipanggil tapi access_token kosong.")

    save_config(path, config)
    return config


def ensure_access_token(config: dict[str, Any], path: Path) -> dict[str, Any]:
    if str(config.get("access_token", "")).strip():
        return config
    if str(config.get("refresh_token", "")).strip():
        return refresh_access_token(config, path)
    raise TikTokConfigError("Config TikTok belum lengkap. Field kosong: access_token atau refresh_token")


def build_session(config: dict[str, Any]) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json; charset=UTF-8",
        }
    )
    return session


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = session.request(method, url, json=json_body, timeout=120)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Response TikTok bukan JSON valid. status={response.status_code} body={response.text[:400]}"
        ) from exc

    error = payload.get("error") or {}
    error_code = str(error.get("code", ""))
    if response.status_code >= 400 or (error_code and error_code.lower() != "ok"):
        raise RuntimeError(
            f"TikTok API gagal. status={response.status_code} code={error_code or 'unknown'} "
            f"message={error.get('message', '') or response.text[:300]}"
        )
    return payload


def query_creator_info(session: requests.Session) -> dict[str, Any]:
    payload = request_json(
        session,
        "POST",
        f"{API_BASE}/v2/post/publish/creator_info/query/",
        json_body={},
    )
    return payload.get("data", {})


def detect_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "video/mp4"


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"File JSON harus object: {path}")
    return payload


def normalize_repo_path(value: str | None) -> str | None:
    if not value:
        return None
    normalized = str(value).replace("\\", "/").removeprefix("./")
    if normalized.startswith("/files/"):
        return "shared/" + normalized.removeprefix("/files/")
    return normalized


def resolve_repo_path(value: str | None) -> Path | None:
    normalized = normalize_repo_path(value)
    if not normalized:
        return None
    path = Path(normalized)
    if path.is_absolute():
        return path
    return ROOT / path


def calculate_upload_plan(video_size: int) -> tuple[int, int]:
    if video_size <= 0:
        raise ValueError("Ukuran video harus lebih besar dari 0.")
    if video_size < 5_000_000:
        return video_size, 1

    chunk_size = min(UPLOAD_CHUNK_SIZE, video_size)
    chunk_count = math.floor(video_size / chunk_size)

    if chunk_count > 1000:
        raise ValueError("Video terlalu besar untuk batas maksimum chunk TikTok.")

    return chunk_size, chunk_count


def init_upload(
    session: requests.Session,
    *,
    config: dict[str, Any],
    file_path: Path,
    title: str,
    direct_post: bool,
) -> dict[str, Any]:
    video_size = file_path.stat().st_size
    chunk_size, chunk_count = calculate_upload_plan(video_size)
    source = str(config.get("source", "FILE_UPLOAD")).strip() or "FILE_UPLOAD"

    if source != "FILE_UPLOAD":
        raise TikTokConfigError(
            "Helper CLI ini saat ini hanya menyiapkan FILE_UPLOAD supaya konsisten dengan shared/ready lokal."
        )

    endpoint = (
        f"{API_BASE}/v2/post/publish/video/init/"
        if direct_post
        else f"{API_BASE}/v2/post/publish/inbox/video/init/"
    )

    body: dict[str, Any] = {
        "source_info": {
            "source": source,
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": chunk_count,
        }
    }

    if direct_post:
        body["post_info"] = {
            "title": title,
            "privacy_level": config["privacy_level"],
            "disable_comment": bool(config.get("disable_comment", False)),
            "disable_duet": bool(config.get("disable_duet", False)),
            "disable_stitch": bool(config.get("disable_stitch", False)),
            "brand_content_toggle": bool(config.get("brand_content_toggle", False)),
            "brand_organic_toggle": bool(config.get("brand_organic_toggle", False)),
            "is_aigc": bool(config.get("is_aigc", False)),
        }

    payload = request_json(session, "POST", endpoint, json_body=body)
    return payload.get("data", {})


def upload_file(upload_url: str, file_path: Path) -> dict[str, Any]:
    video_size = file_path.stat().st_size
    chunk_size, chunk_count = calculate_upload_plan(video_size)
    mime_type = detect_mime_type(file_path)
    session = requests.Session()

    offset = 0
    response_snapshots: list[dict[str, Any]] = []
    with file_path.open("rb") as handle:
        for index in range(chunk_count):
            remaining = video_size - offset
            current_size = remaining if index == chunk_count - 1 else chunk_size
            chunk = handle.read(current_size)
            if len(chunk) != current_size:
                raise RuntimeError("Gagal membaca file video sesuai ukuran chunk yang diharapkan.")

            start_byte = offset
            end_byte = offset + current_size - 1
            headers = {
                "Content-Type": mime_type,
                "Content-Length": str(current_size),
                "Content-Range": f"bytes {start_byte}-{end_byte}/{video_size}",
            }
            response = session.put(upload_url, headers=headers, data=chunk, timeout=300)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Upload chunk TikTok gagal. status={response.status_code} body={response.text[:300]}"
                )
            response_snapshots.append(
                {
                    "chunk_index": index + 1,
                    "status_code": response.status_code,
                    "etag": response.headers.get("ETag"),
                }
            )
            offset += current_size

    return {
        "video_size": video_size,
        "chunk_size": chunk_size,
        "total_chunk_count": chunk_count,
        "responses": response_snapshots,
    }


def fetch_status(session: requests.Session, publish_id: str) -> dict[str, Any]:
    payload = request_json(
        session,
        "POST",
        f"{API_BASE}/v2/post/publish/status/fetch/",
        json_body={"publish_id": publish_id},
    )
    return payload.get("data", {})


def derive_title(raw_title: str, suffix: str) -> str:
    title = " ".join(raw_title.split()).strip()
    if suffix.strip():
        title = f"{title} {suffix.strip()}".strip()
    return title[:2200]


def derive_tiktok_title(caption_result: dict[str, Any]) -> str:
    caption_packs = caption_result.get("caption_pack") or []
    if not isinstance(caption_packs, list):
        caption_packs = []
    tiktok_pack = next(
        (
            item
            for item in caption_packs
            if isinstance(item, dict) and item.get("platform") in {"tiktok", "tiktok_video"}
        ),
        None,
    )
    pack = tiktok_pack or next((item for item in caption_packs if isinstance(item, dict)), {})
    caption = " ".join(str(pack.get("caption") or "").split()).strip()
    hashtags = pack.get("hashtags") or caption_result.get("hashtags") or []
    if not isinstance(hashtags, list):
        hashtags = []
    hashtag_text = " ".join(str(item).strip() for item in hashtags if str(item).strip())
    return " ".join(part for part in [caption, hashtag_text] if part).strip()


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def command_creator_info(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = ensure_access_token(load_config(config_path), config_path)
    session = build_session(config)
    info = query_creator_info(session)
    print_json(info)
    return 0


def command_status(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = ensure_access_token(load_config(config_path), config_path)
    session = build_session(config)
    status = fetch_status(session, args.publish_id)
    print_json(status)
    return 0


def command_post_video(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    config = ensure_access_token(load_config(config_path), config_path)

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        raise SystemExit(f"File video tidak ditemukan: {file_path}")

    post_mode = (args.post_mode or str(config.get("post_mode", "UPLOAD"))).strip().upper()
    direct_post = post_mode == "DIRECT_POST"

    if direct_post:
        creator_info = query_creator_info(build_session(config))
        privacy_options = creator_info.get("privacy_level_options") or []
        desired_privacy = str(config.get("privacy_level", "SELF_ONLY"))
        if privacy_options and desired_privacy not in privacy_options:
            raise SystemExit(
                "privacy_level di config tidak termasuk opsi creator saat ini: "
                + ", ".join(map(str, privacy_options))
            )

    title = derive_title(args.title, str(config.get("title_suffix", "")))
    session = build_session(config)
    init_data = init_upload(
        session,
        config=config,
        file_path=file_path,
        title=title,
        direct_post=direct_post,
    )
    publish_id = str(init_data.get("publish_id", "")).strip()
    upload_url = str(init_data.get("upload_url", "")).strip()

    if not publish_id:
        raise RuntimeError("TikTok tidak mengembalikan publish_id.")

    upload_result = None
    if upload_url:
        upload_result = upload_file(upload_url, file_path)

    status = fetch_status(session, publish_id)
    status_checked_at = utc_now_iso()
    result = {
        "job_id": args.job_id,
        "stage": "WF-04_PUBLISH_TIKTOK",
        "status": "TIKTOK_UPLOAD_INITIATED",
        "published_at": None,
        "status_checked_at": status_checked_at,
        "publish_mode": "DIRECT_POST" if direct_post else "UPLOAD",
        "publish_id": publish_id,
        "video_path": args.file,
        "title_used": title,
        "upload_result": upload_result,
        "status_snapshot": status,
    }

    result["status_checked_at"] = status.get("checked_at") or status_checked_at
    if args.result_file:
        result_path = Path(args.result_file)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print_json(result)
    return 0


def command_post_job(args: argparse.Namespace) -> int:
    job_dir = Path(args.job_dir)
    if not job_dir.is_absolute():
        job_dir = (ROOT / job_dir).resolve()
    if not job_dir.exists():
        raise RuntimeError(f"Folder job tidak ditemukan: {job_dir}")

    manifest = read_json(job_dir / "manifest.json")
    caption_result = read_json(job_dir / "caption_result.json")
    job_id = str(caption_result.get("job_id") or manifest.get("job_id") or job_dir.name)
    file_path = args.file or normalize_repo_path(manifest.get("clip_path"))
    if not file_path:
        raise RuntimeError("clip_path tidak ditemukan di manifest dan --file tidak diisi.")

    title = args.title or derive_tiktok_title(caption_result)
    if not title:
        raise RuntimeError("Caption TikTok tidak ditemukan di caption_result dan --title tidak diisi.")

    result_file = args.result_file
    if result_file is None:
        result_file = str(job_dir / "tiktok_publish_result.json")

    delegated_args = argparse.Namespace(
        config=args.config,
        file=str(resolve_repo_path(file_path) or file_path),
        title=title,
        job_id=job_id,
        result_file=result_file,
        post_mode=args.post_mode,
    )
    return command_post_video(delegated_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Helper CLI untuk TikTok Content Posting API."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path ke shared/config/tiktok_posting.json",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    creator_info_parser = subparsers.add_parser(
        "creator-info",
        help="Query creator info untuk validasi akun dan opsi privacy TikTok.",
    )
    creator_info_parser.set_defaults(func=command_creator_info)

    status_parser = subparsers.add_parser(
        "status",
        help="Cek status publish TikTok berdasarkan publish_id.",
    )
    status_parser.add_argument("--publish-id", required=True, help="publish_id dari TikTok")
    status_parser.set_defaults(func=command_status)

    post_parser = subparsers.add_parser(
        "post-video",
        help="Init upload, kirim file video, lalu cek status awal TikTok.",
    )
    post_parser.add_argument("--file", required=True, help="Path ke video lokal")
    post_parser.add_argument("--title", required=True, help="Caption/title TikTok")
    post_parser.add_argument("--job-id", default=None, help="job_id opsional untuk result file")
    post_parser.add_argument(
        "--result-file",
        default=None,
        help="Path output JSON opsional, misalnya shared/ready/<job>/tiktok_publish_result.json",
    )
    post_parser.add_argument(
        "--post-mode",
        choices=["UPLOAD", "DIRECT_POST"],
        help="Override post mode dari config lokal",
    )
    post_parser.set_defaults(func=command_post_video)

    post_job_parser = subparsers.add_parser(
        "post-job",
        help="Upload TikTok dari folder shared/ready/<job_id> memakai manifest dan caption_result.",
    )
    post_job_parser.add_argument("--job-dir", required=True, help="Path folder job")
    post_job_parser.add_argument("--file", default=None, help="Override path video")
    post_job_parser.add_argument("--title", default=None, help="Override caption/title TikTok")
    post_job_parser.add_argument(
        "--result-file",
        default=None,
        help="Path output JSON. Default: <job-dir>/tiktok_publish_result.json",
    )
    post_job_parser.add_argument(
        "--post-mode",
        choices=["UPLOAD", "DIRECT_POST"],
        help="Override post mode dari config lokal",
    )
    post_job_parser.set_defaults(func=command_post_job)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except TikTokConfigError as error:
        print_json(
            {
                "stage": "WF-04_PUBLISH_TIKTOK",
                "status": "TIKTOK_CONFIG_INVALID",
                "error_message": str(error),
            }
        )
        return 1
    except Exception as error:
        print_json(
            {
                "stage": "WF-04_PUBLISH_TIKTOK",
                "status": "TIKTOK_UPLOAD_FAILED",
                "error_message": str(error) or "TikTok helper gagal tanpa detail.",
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
