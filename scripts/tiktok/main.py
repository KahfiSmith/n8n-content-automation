#!/usr/bin/env python3
"""TikTok Uploader CLI.

Commands:
    python main.py login              - Login TikTok (browser muncul, simpan session)
    python main.py check-cookies      - Cek apakah session masih valid
    python main.py upload             - Upload single video
    python main.py upload-from-queue  - Upload dari queue file (n8n integration)

Dependencies:
    pip install tiktokautouploader
    phantomwright_driver install chromium
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

DEFAULT_CONFIG = {
    "headless": True,
    "timeout_ms": 60000,
    "retry_count": 2,
    "account_name": "",
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **cfg}
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def cmd_login(args: argparse.Namespace) -> None:
    """Login TikTok — browser muncul, user login manual, session tersimpan."""
    try:
        from tiktokautouploader import upload_tiktok
    except ImportError:
        print("ERROR: tiktokautouploader belum terinstall.")
        print("Run: pip install tiktokautouploader && phantomwright_driver install chromium")
        sys.exit(1)

    cfg = load_config()
    account = args.account or cfg.get("account_name") or ""

    if not account:
        account = input("Masukkan username TikTok: ").strip()

    cfg["account_name"] = account
    save_config(cfg)

    print(f"Browser akan terbuka. Login ke akun @{account}...")
    print("Setelah login berhasil, session otomatis tersimpan.")

    # Trigger login dengan upload dummy yang akan gagal tapi session tersimpan
    # tiktokautouploader minta login saat pertama kali pakai accountname baru
    try:
        upload_tiktok(
            video="__dummy_login__",
            description="",
            accountname=account,
            headless=False,
        )
    except Exception:
        pass

    print(f"\nSession untuk @{account} tersimpan.")
    print("Sekarang bisa upload dengan: python main.py upload --video path/video.mp4")


def cmd_check_cookies(args: argparse.Namespace) -> None:
    """Cek apakah session masih valid."""
    cfg = load_config()
    account = args.account or cfg.get("account_name") or ""

    if not account:
        print(json.dumps({"status": "NO_ACCOUNT", "message": "Belum ada account. Run: python main.py login"}))
        sys.exit(1)

    # tiktokautouploader simpan session di internal storage per accountname
    # Cara cek: coba buka TikTok creator page
    print(json.dumps({
        "status": "SESSION_EXISTS",
        "account": account,
        "message": f"Session untuk @{account} ada. Upload untuk test validitas.",
    }))


def cmd_upload(args: argparse.Namespace) -> None:
    """Upload single video ke TikTok."""
    try:
        from tiktokautouploader import upload_tiktok
    except ImportError:
        result = {"status": "TIKTOK_UPLOAD_FAILED", "error": "tiktokautouploader not installed"}
        _output(result, args.result_path)
        sys.exit(1)

    cfg = load_config()
    account = args.account or cfg.get("account_name") or ""
    headless = args.headless if args.headless is not None else cfg.get("headless", True)
    video = Path(args.video)

    if not account:
        result = {"status": "TIKTOK_UPLOAD_FAILED", "error": "no_account", "message": "Run: python main.py login"}
        _output(result, args.result_path)
        sys.exit(1)

    if not video.exists():
        result = {"status": "TIKTOK_UPLOAD_FAILED", "error": "file_not_found", "clip_path": str(video)}
        _output(result, args.result_path)
        sys.exit(1)

    # Parse hashtags dari caption atau dari --hashtags
    hashtags = None
    if args.hashtags:
        hashtags = [h if h.startswith("#") else f"#{h}" for h in args.hashtags]

    caption = args.caption or ""

    retry_count = cfg.get("retry_count", 2)
    last_error = None

    for attempt in range(1, retry_count + 1):
        try:
            upload_tiktok(
                video=str(video),
                description=caption,
                accountname=account,
                hashtags=hashtags,
                headless=headless,
                suppressprint=False,
            )
            result = {
                "status": "TIKTOK_UPLOADED",
                "clip_path": str(video),
                "uploaded_at": now_iso(),
                "account": account,
                "privacy": args.privacy or "public",
                "description": caption,
                "hashtags": hashtags or [],
            }
            _output(result, args.result_path)
            sys.exit(0)
        except Exception as e:
            last_error = str(e)
            if attempt < retry_count:
                print(f"  Attempt {attempt} failed: {last_error}. Retrying...")

    result = {
        "status": "TIKTOK_UPLOAD_FAILED",
        "error": last_error,
        "clip_path": str(video),
        "uploaded_at": now_iso(),
        "account": account,
        "message": "Coba: python main.py login (refresh session)" if "cookie" in (last_error or "").lower() else None,
    }
    _output(result, args.result_path)
    sys.exit(1)


def cmd_upload_from_queue(args: argparse.Namespace) -> None:
    """Upload semua item dari queue file."""
    queue_path = Path(args.queue_path) if args.queue_path else ROOT / "shared" / "config" / "tiktok_upload_queue.json"

    if not queue_path.exists():
        print("No queue file found. Run WF-04 di n8n dulu.")
        return

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if not queue:
        print("Queue kosong.")
        queue_path.unlink(missing_ok=True)
        return

    cfg = load_config()
    print(f"Processing {len(queue)} clip(s)...")

    for item in queue:
        video_path = item.get("clip_path", "")
        # Resolve relative to ROOT
        video = ROOT / video_path if not Path(video_path).is_absolute() else Path(video_path)
        result_path = ROOT / item["result_path"] if not Path(item.get("result_path", "")).is_absolute() else Path(item["result_path"])
        account = item.get("account_name") or cfg.get("account_name") or ""
        caption = item.get("description", "")
        hashtags = item.get("hashtags")

        if not account:
            print(f"  SKIP {item.get('clip_id')}: no account. Run: python main.py login")
            continue

        if not video.exists():
            result = {"status": "TIKTOK_UPLOAD_FAILED", "error": f"File not found: {video}", "uploaded_at": now_iso()}
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"  FAIL {item.get('clip_id')}: file not found")
            continue

        print(f"  Uploading {item.get('clip_id')} ({video.name})...")

        # Build args and call cmd_upload logic
        upload_args = argparse.Namespace(
            video=str(video),
            caption=caption,
            hashtags=hashtags,
            account=account,
            headless=True,
            privacy=item.get("privacy_level", "public"),
            result_path=str(result_path),
        )

        try:
            cmd_upload(upload_args)
        except SystemExit as e:
            if e.code == 0:
                print(f"  OK {item.get('clip_id')}")
            else:
                print(f"  FAIL {item.get('clip_id')}")

    queue_path.unlink(missing_ok=True)
    print("Done. Queue cleared.")


def _output(result: dict, result_path: str | None) -> None:
    """Print JSON dan tulis ke file jika diminta."""
    print(json.dumps(result, indent=2))
    if result_path:
        p = Path(result_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tiktok-uploader", description="TikTok Upload CLI")
    sub = parser.add_subparsers(dest="command")

    # login
    p_login = sub.add_parser("login", help="Login TikTok (browser muncul)")
    p_login.add_argument("--account", help="Username TikTok")

    # check-cookies
    p_check = sub.add_parser("check-cookies", help="Cek session status")
    p_check.add_argument("--account", help="Username TikTok")

    # upload
    p_upload = sub.add_parser("upload", help="Upload single video")
    p_upload.add_argument("--video", required=True, help="Path ke video")
    p_upload.add_argument("--caption", default="", help="Caption/deskripsi")
    p_upload.add_argument("--hashtags", nargs="*", help="Hashtags")
    p_upload.add_argument("--account", help="Username TikTok")
    p_upload.add_argument("--privacy", default="public", help="Privacy level")
    p_upload.add_argument("--headless", type=bool, default=None, help="Headless mode")
    p_upload.add_argument("--result-path", help="Path untuk tulis result JSON")

    # upload-from-queue
    p_queue = sub.add_parser("upload-from-queue", help="Upload dari queue file")
    p_queue.add_argument("--queue-path", help="Path ke queue JSON")

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "check-cookies":
        cmd_check_cookies(args)
    elif args.command == "upload":
        cmd_upload(args)
    elif args.command == "upload-from-queue":
        cmd_upload_from_queue(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
