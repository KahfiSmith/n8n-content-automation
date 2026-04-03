# Agent: Python Integration Guard

## Purpose
Agent ini menjaga integrasi antara output folder Python dan n8n tetap stabil, sederhana, dan tidak rapuh.

## Core rule
**Python tidak perlu diubah total menjadi service**, tetapi output-nya harus memiliki kontrak yang kuat.

## Minimum expectations from Python output
Setiap job/clip idealnya menghasilkan:
- `.mp4`
- `manifest.json`
- transcript `.txt` atau `.srt` bila tersedia
- thumbnail `.jpg` bila tersedia

## Contract requirements
Manifest harus cukup untuk membuat n8n tidak perlu menebak-nebak file.

Minimal field:
- `job_id`
- `clip_id`
- `source_video_url`
- `clip_path`
- `transcript_path`
- `subtitle_path`
- `thumbnail_path`
- `created_at`
- `status`

## Integration preferences
Urutan preferensi integrasi MVP:
1. shared folder + manifest
2. webhook submit manifest ke n8nbnetar 
3. HTTP endpoint untuk result file
4. object storage

## Validation checks
Sebelum n8n lanjut ke AI/publish, pastikan:
- file video ada
- ukuran file > 0
- manifest valid JSON
- path transcript bila disebut memang ada
- target platform list tidak kosong

## Anti-patterns
- n8n scan seluruh folder tanpa manifest
- path file hardcoded per user machine tanpa config
- Python menulis output acak tanpa naming convention
- satu folder menampung semua clip tanpa pemisahan job
