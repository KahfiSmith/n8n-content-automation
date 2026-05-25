#!/usr/bin/env python3
"""Build CSV/JSON upload queue from a ready job folder.

Output ini untuk semi-manual upload: satu baris per clip, caption siap copy,
dan flag review jika caption masih fallback global, bukan caption spesifik clip.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
COPY_PREFIX_RE = re.compile(
    r"^\s*[\[(]?\s*(?:clip|video|caption|judul|title|bagian|part)[\s_-]*\d{1,3}\s*[\])\].:;\-_]*\s*",
    re.IGNORECASE,
)
LEADING_COPY_PUNCT_RE = re.compile(r"^[\s\-:.;)\]\u2013\u2014\u2212]+")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"File JSON harus object: {path}")
    return payload


def normalize_repo_path(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\\", "/").removeprefix("./")
    if text.startswith("/files/"):
        return "shared/" + text.removeprefix("/files/")
    return text


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def normalize_hashtags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    for item in value:
        tag = str(item or "").strip()
        if not tag:
            continue
        tags.append(tag if tag.startswith("#") else f"#{tag}")
    return tags


def strip_copy_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    previous = None
    while text and text != previous:
        previous = text
        text = COPY_PREFIX_RE.sub("", text).strip()
    return LEADING_COPY_PUNCT_RE.sub("", text).strip()


def derive_title(caption: str, fallback: str) -> str:
    text = strip_copy_prefix(caption)
    if not text:
        return fallback[:100]
    for separator in [".", "!", "?", "\n"]:
        if separator in text:
            candidate = text.split(separator, 1)[0].strip()
            if candidate:
                return strip_copy_prefix(candidate)[:100]
    return strip_copy_prefix(text)[:100]


def get_clips(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw_clips = manifest.get("clips")
    if isinstance(raw_clips, list) and raw_clips:
        clips = []
        for index, item in enumerate(raw_clips, start=1):
            if not isinstance(item, dict):
                continue
            clip_path = normalize_repo_path(item.get("clip_path") or item.get("file_path"))
            clips.append(
                {
                    "clip_index": index,
                    "clip_id": str(item.get("clip_id") or f"clip_{index:02d}"),
                    "file_name": str(item.get("file_name") or Path(clip_path).name),
                    "clip_path": clip_path,
                }
            )
        if clips:
            return clips

    clip_path = normalize_repo_path(manifest.get("clip_path"))
    return [
        {
            "clip_index": 1,
            "clip_id": str(manifest.get("clip_id") or "clip_01"),
            "file_name": Path(clip_path).name,
            "clip_path": clip_path,
        }
    ]


def find_platform_pack(packs: Any, platform: str) -> dict[str, Any] | None:
    if not isinstance(packs, list):
        return None
    for pack in packs:
        if isinstance(pack, dict) and pack.get("platform") == platform:
            return pack
    for pack in packs:
        if isinstance(pack, dict):
            return pack
    return None


def find_clip_pack(
    caption_result: dict[str, Any],
    clip: dict[str, Any],
    platform: str,
) -> tuple[dict[str, Any] | None, str]:
    clip_packs = caption_result.get("clip_caption_pack")
    if not isinstance(clip_packs, list):
        return None, ""

    clip_id = str(clip.get("clip_id") or "")
    clip_path = normalize_repo_path(clip.get("clip_path"))
    file_name = str(clip.get("file_name") or "")

    for item in clip_packs:
        if not isinstance(item, dict):
            continue
        item_clip_id = str(item.get("clip_id") or "")
        item_clip_path = normalize_repo_path(item.get("clip_path"))
        item_file_name = str(item.get("file_name") or Path(item_clip_path).name)
        matched = item_clip_id == clip_id or item_clip_path == clip_path or item_file_name == file_name
        if not matched:
            continue
        pack = find_platform_pack(item.get("captions") or item.get("caption_pack"), platform)
        if pack:
            return pack, "clip_caption_pack"
    return None, ""


def build_rows(manifest: dict[str, Any], caption_result: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    job_id = str(caption_result.get("job_id") or manifest.get("job_id") or "")
    clips = get_clips(manifest)
    clip_caption_source = str(caption_result.get("clip_caption_source") or "").strip()
    global_pack = find_platform_pack(caption_result.get("caption_pack"), platform) or {}
    global_caption = str(global_pack.get("caption") or "").strip()
    global_hashtags = normalize_hashtags(global_pack.get("hashtags") or caption_result.get("hashtags"))

    rows: list[dict[str, Any]] = []
    for clip in clips:
        clip_pack, source = find_clip_pack(caption_result, clip, platform)
        needs_review = False
        warning = ""

        if clip_pack:
            caption = strip_copy_prefix(clip_pack.get("caption"))
            hashtags = normalize_hashtags(clip_pack.get("hashtags"))
            if clip_caption_source == "generated_variant_from_global_metadata":
                source = clip_caption_source
                needs_review = True
                warning = "caption unik dari metadata global; review singkat sebelum publish"
        else:
            caption = strip_copy_prefix(global_caption)
            hashtags = global_hashtags
            source = "caption_pack_fallback"
            needs_review = True
            warning = "caption fallback global; belum unik per clip"

        caption_full = strip_copy_prefix(" ".join(part for part in [caption, " ".join(hashtags)] if part).strip())
        clip_path = normalize_repo_path(clip["clip_path"])
        title = strip_copy_prefix(derive_title(caption, str(clip["clip_id"])))
        rows.append(
            {
                "clip_path": clip_path,
                "title": title,
                "caption_full": caption_full,
                "hashtags": " ".join(hashtags),
                "upload_status": "todo",
                "published_url": "",
                "notes": "",
                "job_id": job_id,
                "platform": platform,
                "clip_index": clip["clip_index"],
                "clip_id": clip["clip_id"],
                "file_name": clip["file_name"],
                "file_exists": str(resolve_path(clip_path).exists()).lower(),
                "caption": caption,
                "caption_source": source,
                "needs_review": str(needs_review).lower(),
                "warning": warning,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "clip_path",
        "title",
        "caption_full",
        "hashtags",
        "upload_status",
        "published_url",
        "notes",
        "file_name",
        "platform",
        "job_id",
        "clip_index",
        "clip_id",
        "file_exists",
        "caption",
        "caption_source",
        "needs_review",
        "warning",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, Any]], manifest: dict[str, Any], platform: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job_id": manifest.get("job_id"),
        "platform": platform,
        "clip_count": len(rows),
        "rows": rows,
        "warnings": sorted({row["warning"] for row in rows if row["warning"]}),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build semi-manual upload queue CSV per clip.")
    parser.add_argument("--job-dir", required=True, help="Path folder shared/ready/<job_id>")
    parser.add_argument("--platform", default="youtube_shorts", help="Target platform, default: youtube_shorts")
    parser.add_argument("--output", default=None, help="Output CSV path")
    parser.add_argument("--json-output", default=None, help="Optional output JSON path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero jika ada caption fallback/global yang perlu review.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        job_dir = Path(args.job_dir)
        if not job_dir.is_absolute():
            job_dir = ROOT / job_dir

        manifest = read_json(job_dir / "manifest.json")
        caption_result = read_json(job_dir / "caption_result.json")
        platform = str(args.platform).strip() or "youtube_shorts"
        rows = build_rows(manifest, caption_result, platform)

        output = Path(args.output) if args.output else job_dir / f"upload_queue_{platform}.csv"
        json_output = Path(args.json_output) if args.json_output else job_dir / f"upload_queue_{platform}.json"
        write_csv(output, rows)
        write_json(json_output, rows, manifest, platform)

        needs_review = sum(1 for row in rows if row["needs_review"] == "true")
        summary = {
            "status": "UPLOAD_QUEUE_READY" if needs_review == 0 else "UPLOAD_QUEUE_READY_NEEDS_REVIEW",
            "job_id": manifest.get("job_id"),
            "platform": platform,
            "clip_count": len(rows),
            "rows_needing_review": needs_review,
            "csv_path": normalize_repo_path(str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output)),
            "json_path": normalize_repo_path(str(json_output.relative_to(ROOT)) if json_output.is_relative_to(ROOT) else str(json_output)),
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 1 if args.strict and needs_review else 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "UPLOAD_QUEUE_FAILED",
                    "error_message": str(error),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
