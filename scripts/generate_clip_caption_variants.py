#!/usr/bin/env python3
"""Generate per-clip caption variants from an existing caption_result.json.

Ini fallback praktis untuk semi-manual upload saat caption lama masih global
dan belum punya caption unik per clip.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent


PLATFORM_HASHTAGS: dict[str, list[str]] = {}


CLIP_POSITION_HOOKS = [
    "Mulai dari sini.",
    "Ini bagian yang sering dilewat.",
    "Simpan bagian ini.",
    "Yang ini krusial.",
    "Perhatikan baik-baik.",
    "Ini yang bikin beda.",
    "Sini rahasianya.",
    "Ini penutup yang ngena.",
]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"File JSON harus object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_repo_path(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\\", "/").removeprefix("./")
    if text.startswith("/files/"):
        return "shared/" + text.removeprefix("/files/")
    return text


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


def dedupe(items: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def get_clips(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw_clips = manifest.get("clips")
    if isinstance(raw_clips, list) and raw_clips:
        clips: list[dict[str, Any]] = []
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


def platform_hashtags(platform: str, base_hashtags: list[str]) -> list[str]:
    return dedupe(base_hashtags or PLATFORM_HASHTAGS.get(platform, []), limit=8)


def caption_for_clip(
    index: int,
    platform: str,
    base_caption: str,
    total_clips: int,
    transcript_segment: str = "",
) -> str:
    if not base_caption:
        return ""

    if total_clips <= 1:
        return base_caption

    sentences = [s.strip() for s in base_caption.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if not sentences:
        sentences = [base_caption]

    if transcript_segment:
        seg_sentences = [s.strip() for s in transcript_segment.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        seg_sentences = [s for s in seg_sentences if len(s) > 10][:2]
        if seg_sentences:
            hook = CLIP_POSITION_HOOKS[(index - 1) % len(CLIP_POSITION_HOOKS)]
            caption = f"{hook} {'. '.join(seg_sentences)}."
            if platform == "facebook_reels":
                caption = caption.replace("ngebahas", "membahas")
            return caption.strip()

    total = len(sentences)
    if total == 1:
        chunk = sentences
    else:
        chunk_size = max(1, total // total_clips)
        start = (index - 1) * chunk_size
        end = start + chunk_size if index < total_clips else total
        chunk = sentences[start:end]
        if not chunk:
            chunk = [sentences[-1]]

    hook = CLIP_POSITION_HOOKS[(index - 1) % len(CLIP_POSITION_HOOKS)]
    caption = f"{hook} {'. '.join(chunk)}."
    if platform == "facebook_reels":
        caption = caption.replace("ngebahas", "membahas")
    return caption.strip()


def update_caption_result(
    manifest: dict[str, Any],
    caption_result: dict[str, Any],
    platforms: list[str],
) -> dict[str, Any]:
    clips = get_clips(manifest)
    base_hashtags = normalize_hashtags(caption_result.get("hashtags"))
    base_caption = ""
    caption_pack = caption_result.get("caption_pack")
    if isinstance(caption_pack, list):
        for item in caption_pack:
            if isinstance(item, dict) and item.get("caption"):
                base_caption = str(item["caption"]).strip()
                break

    transcript_segments: dict[int, str] = {}
    clip_caption_pack_existing = caption_result.get("clip_caption_pack")
    if isinstance(clip_caption_pack_existing, list):
        for item in clip_caption_pack_existing:
            if not isinstance(item, dict):
                continue
            idx = item.get("clip_index")
            transcript = str(item.get("transcript_text") or item.get("transcript") or "").strip()
            if idx and transcript:
                transcript_segments[int(idx)] = transcript

    transcript_text = str(caption_result.get("transcript_text") or manifest.get("transcript_text") or "").strip()
    if transcript_text and not transcript_segments:
        segment_len = max(100, len(transcript_text) // max(1, len(clips)))
        for i, clip in enumerate(clips):
            start = i * segment_len
            end = start + segment_len + 50
            transcript_segments[clip["clip_index"]] = transcript_text[start:end]

    total_clips = len(clips)
    clip_caption_pack = []
    for clip in clips:
        clip_idx = int(clip["clip_index"])
        segment = transcript_segments.get(clip_idx, "")
        captions = []
        for platform in platforms:
            captions.append(
                {
                    "platform": platform,
                    "caption": caption_for_clip(clip_idx, platform, base_caption, total_clips, segment),
                    "hashtags": platform_hashtags(platform, base_hashtags),
                }
            )
        clip_caption_pack.append(
            {
                "clip_id": clip["clip_id"],
                "clip_index": clip["clip_index"],
                "file_name": clip["file_name"],
                "clip_path": clip["clip_path"],
                "captions": captions,
            }
        )

    warnings = list(caption_result.get("caption_warnings") or [])
    warning = "clip_caption_pack generated from global metadata; review before publishing if clip content differs"
    if warning not in warnings:
        warnings.append(warning)

    updated = dict(caption_result)
    updated["clip_count"] = len(clips)
    updated["clips"] = clips
    updated["clip_caption_source"] = "generated_variant_from_global_metadata"
    updated["clip_caption_pack"] = clip_caption_pack
    updated["caption_warnings"] = warnings
    return updated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate unique per-clip caption variants.")
    parser.add_argument("--job-dir", required=True, help="Path folder shared/ready/<job_id>")
    parser.add_argument(
        "--platforms",
        default="youtube_shorts,facebook_reels",
        help="Comma-separated platforms, default: youtube_shorts,facebook_reels",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    job_dir = Path(args.job_dir)
    if not job_dir.is_absolute():
        job_dir = ROOT / job_dir
    platforms = [item.strip() for item in str(args.platforms).split(",") if item.strip()]
    manifest_path = job_dir / "manifest.json"
    caption_path = job_dir / "caption_result.json"

    manifest = read_json(manifest_path)
    caption_result = read_json(caption_path)
    updated = update_caption_result(manifest, caption_result, platforms)
    write_json(caption_path, updated)

    print(
        json.dumps(
            {
                "status": "CLIP_CAPTION_VARIANTS_GENERATED",
                "job_id": updated.get("job_id"),
                "clip_count": updated.get("clip_count"),
                "platforms": platforms,
                "caption_result_path": normalize_repo_path(str(caption_path.relative_to(ROOT))),
                "warning": updated["caption_warnings"][-1],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
