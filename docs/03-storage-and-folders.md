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
├── ready/
│   └── job_<timestamp>_<shortid>/
│       ├── clip_1.mp4
│       ├── clip_2.mp4
│       ├── transcript.txt
│       ├── thumbnail.jpg
│       └── manifest.json
├── published/
└── failed/
```

---

## Penjelasan folder

### `ready/`
Folder utama yang dibaca n8n. Hanya job yang sudah final dan lengkap yang boleh masuk ke sini.

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
  "platform_targets": ["youtube_shorts", "tiktok", "facebook_reels"],
  "approval_mode": "required",
  "created_at": "2026-03-31T21:30:10+07:00",
  "status": "ready"
}
```

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
- setelah diproses, job bisa dipindah ke `published/` atau ditandai lewat file status.
- jika job gagal, simpan context error di `failed/` atau incident store.
