import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_job_id():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"job_{timestamp}_{suffix}"


def repo_path(path):
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def fetch_source_metadata(url):
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--skip-download",
        "-J",
        str(url),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {}
        raw = json.loads(result.stdout)
        item = raw["entries"][0] if isinstance(raw, dict) and raw.get("entries") else raw
        if not isinstance(item, dict):
            return {}
        return {
            "source_video_title": item.get("title"),
            "source_video_uploader": item.get("uploader"),
            "source_video_duration": item.get("duration"),
            "source_video_description": item.get("description"),
        }
    except Exception:
        return {}


def list_clip_entries(job_dir):
    clips = []
    for index, file_path in enumerate(sorted(Path(job_dir).glob("clip_*.mp4")), start=1):
        clips.append(
            {
                "clip_id": f"clip_{index:02d}",
                "file_name": file_path.name,
                "clip_path": repo_path(file_path),
                "status": "ready",
                "created_at": now_iso(),
            }
        )
    return clips


def write_job_manifest(
    job_dir,
    source_video_url,
    source_video_id,
    platform_targets=None,
    approval_mode="required",
    subtitle_enabled=False,
    crop_mode="default",
    ratio="9:16",
    padding=None,
    **source_meta,
):
    job_dir_path = Path(job_dir)
    job_dir_path.mkdir(parents=True, exist_ok=True)
    job_id = job_dir_path.name
    clips = list_clip_entries(job_dir_path)
    first_clip = clips[0] if clips else {}
    targets = platform_targets if isinstance(platform_targets, list) and platform_targets else ["youtube_shorts"]

    manifest_path = job_dir_path / "manifest.json"
    payload = {
        "job_id": job_id,
        "source_video_url": source_video_url,
        "source_video_id": source_video_id,
        "source_video_title": source_meta.get("source_video_title"),
        "source_video_uploader": source_meta.get("source_video_uploader"),
        "source_video_duration": source_meta.get("source_video_duration"),
        "source_video_description": source_meta.get("source_video_description"),
        "clip_id": first_clip.get("clip_id"),
        "clip_path": first_clip.get("clip_path"),
        "clips": clips,
        "clip_count": len(clips),
        "transcript_path": None,
        "thumbnail_path": None,
        "platform_targets": targets,
        "approval_mode": approval_mode or "required",
        "subtitle_enabled": bool(subtitle_enabled),
        "crop_mode": crop_mode,
        "ratio": ratio,
        "padding": padding,
        "status": "ready",
        "created_at": now_iso(),
        "manifest_path": repo_path(manifest_path),
    }

    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
