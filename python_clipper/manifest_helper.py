import json
import os
import uuid
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
READY_DIR = os.path.join(PROJECT_ROOT, "shared", "ready")


def build_job_id(prefix="job"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:6]
    return f"{prefix}_{timestamp}_{short_id}"


def _to_repo_relative(path):
    abs_path = os.path.abspath(path)
    try:
        common = os.path.commonpath([PROJECT_ROOT, abs_path])
    except ValueError:
        common = ""
    if common == PROJECT_ROOT:
        rel_path = os.path.relpath(abs_path, PROJECT_ROOT)
        return rel_path.replace(os.sep, "/")
    return abs_path.replace(os.sep, "/")


def _normalize_targets(platform_targets):
    if not platform_targets:
        return ["youtube_shorts"]
    if isinstance(platform_targets, str):
        return [platform_targets]
    if isinstance(platform_targets, list):
        return [str(item).strip() for item in platform_targets if str(item).strip()]
    return ["youtube_shorts"]


def _guess_optional_asset(job_dir, filenames):
    for name in filenames:
        path = os.path.join(job_dir, name)
        if os.path.isfile(path):
            return _to_repo_relative(path)
    return None


def collect_clip_outputs(job_dir):
    clip_files = []
    for name in sorted(os.listdir(job_dir)):
        path = os.path.join(job_dir, name)
        if os.path.isfile(path) and name.lower().endswith(".mp4"):
            clip_files.append(path)

    clips = []
    for idx, path in enumerate(clip_files, start=1):
        clips.append(
            {
                "clip_id": f"clip_{idx:02d}",
                "file_name": os.path.basename(path),
                "clip_path": _to_repo_relative(path),
            }
        )
    return clips


def write_job_manifest(
    job_dir,
    source_video_url,
    source_video_id,
    *,
    platform_targets=None,
    approval_mode="required",
    subtitle_enabled=False,
    crop_mode=None,
    ratio=None,
    padding=None,
    transcript_path=None,
    thumbnail_path=None,
):
    clips = collect_clip_outputs(job_dir)
    if not clips:
        raise ValueError("Tidak ada file clip .mp4 untuk dibuatkan manifest.")

    transcript_rel = transcript_path or _guess_optional_asset(job_dir, ["transcript.txt"])
    thumbnail_rel = thumbnail_path or _guess_optional_asset(job_dir, ["thumbnail.jpg", "thumbnail.jpeg", "thumbnail.png"])

    manifest = {
        "job_id": os.path.basename(job_dir),
        "source_video_id": source_video_id,
        "source_video_url": source_video_url,
        "clip_count": len(clips),
        "clip_path": clips[0]["clip_path"],
        "clips": clips,
        "transcript_path": transcript_rel,
        "thumbnail_path": thumbnail_rel,
        "platform_targets": _normalize_targets(platform_targets),
        "approval_mode": approval_mode or "required",
        "status": "ready",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generator": {
            "subtitle_enabled": bool(subtitle_enabled),
            "crop_mode": crop_mode,
            "ratio": ratio,
            "padding": padding,
        },
    }

    manifest_path = os.path.join(job_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    manifest["manifest_path"] = _to_repo_relative(manifest_path)
    return manifest
