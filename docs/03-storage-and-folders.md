# 03 - Storage and Folders

## Tujuan dokumen
Menetapkan struktur folder dan kontrak file agar handoff dari Python ke n8n stabil dan tanpa proses manual tambahan.

---

## Prinsip folder

1. struktur harus sesederhana mungkin
2. n8n hanya membaca folder `ready/`
3. satu job punya satu folder sendiri
4. manifest selalu berada dekat dengan clip yang bersangkutan
5. nama folder dan file harus deterministik

---

## Struktur yang disarankan

```bash
shared/
├── config/
│   ├── caption_ai.example.json
│   └── caption_ai.json
│   ├── youtube_oauth.example.json
│   └── youtube_oauth.json
├── ready/
│   └── job_<timestamp>_<shortid>/
│       ├── clip_1.mp4
│       ├── clip_2.mp4
│       ├── transcript.txt
│       ├── thumbnail.jpg
│       ├── manifest.json
│       ├── intake_result.json
│       ├── caption_result.json
│       ├── youtube_publish_result_clip_01.json
│       └── youtube_publish_result_clip_02.json
├── published/
└── failed/
```

---

## Penjelasan folder

### `ready/`
Folder utama yang dibaca n8n. Hanya job yang sudah final dan lengkap yang boleh masuk ke sini.

### `config/`
Konfigurasi lokal yang dibaca workflow n8n atau helper CLI. Untuk caption AI, file yang dipakai adalah `caption_ai.json`. Untuk publish YouTube, file yang dipakai adalah `youtube_oauth.json`. File-file ini sebaiknya digenerate dari `.env` dan tidak di-commit.

### `published/`
Job yang sudah selesai publish atau disimpan untuk histori.

### `failed/`
Job yang gagal validasi atau gagal alur automation.

---

## Naming convention

### Job folder
- `job_<YYYYMMDD_HHMMSS>_<shortid>`

Contoh:
- `job_20260331_213010_a1b2c3`

### File names
Gunakan nama tetap jika satu clip per job:
- `clip.mp4`
- `transcript.txt`
- `thumbnail.jpg`
- `manifest.json`

Jika satu job berisi banyak clip, gunakan:
- `clip_01.mp4`
- `clip_01.txt`
- `clip_01.srt`
- `clip_01.jpg`

---

## Contract file utama: manifest.json

Contoh minimal:

```json
{
  "job_id": "job_20260331_213010_a1b2c3",
  "source_video_url": "https://youtube.com/watch?v=xxxx",
  "source_video_id": "xxxx",
  "clip_count": 2,
  "clip_path": "shared/ready/job_20260331_213010_a1b2c3/clip_1.mp4",
  "clips": [
    {
      "clip_id": "clip_01",
      "file_name": "clip_1.mp4",
      "clip_path": "shared/ready/job_20260331_213010_a1b2c3/clip_1.mp4"
    },
    {
      "clip_id": "clip_02",
      "file_name": "clip_2.mp4",
      "clip_path": "shared/ready/job_20260331_213010_a1b2c3/clip_2.mp4"
    }
  ],
  "transcript_path": "shared/ready/job_20260331_213010_a1b2c3/transcript.txt",
  "thumbnail_path": "shared/ready/job_20260331_213010_a1b2c3/thumbnail.jpg",
  "platform_targets": ["youtube_shorts", "facebook_reels"],
  "approval_mode": "required",
  "created_at": "2026-03-31T21:30:10+07:00",
  "status": "ready"
}
```

Catatan:
- jika `platform_targets` tidak dikirim dari UI Python, helper manifest akan mengisi default `["youtube_shorts", "facebook_reels"]`
- gunakan label tetap `youtube_shorts` dan `facebook_reels`, jangan singkat jadi `fb` atau label lain yang tidak konsisten
- `intake_result.json` dipakai sebagai marker dedupe untuk workflow intake
- `caption_result.json` dipakai sebagai marker dedupe untuk workflow caption
- `shared/config/caption_ai.json` dipakai sebagai sumber config lokal untuk workflow caption
- `youtube_publish_result_clip_*.json` dipakai sebagai marker dedupe per clip untuk workflow publish YouTube
- `shared/config/youtube_oauth.json` dipakai sebagai sumber config lokal untuk workflow publish YouTube
- `WF-03` boleh membentuk title upload internal dari caption bila `caption_result.json` tidak menyimpan title

---

## Handoff terbaik untuk MVP

### Opsi terbaik
**Shared folder + manifest JSON**

Kenapa:
- sederhana
- minim dependency
- mudah debug
- cocok lokal dan VPS satu mesin

### Opsi naik kelas nanti
- webhook submit manifest
- HTTP result endpoint
- object storage

---

## Rule penting

- Python menulis hasil final langsung ke `ready/`.
- n8n hanya memproses job dari `ready/`.
- setelah diproses, job bisa ditandai dulu lewat `intake_result.json`, `caption_result.json`, dan `youtube_publish_result_clip_*.json`, lalu dipindah ke `published/` pada stage akhir.
- jika job gagal, simpan context error di `failed/` atau incident store.
