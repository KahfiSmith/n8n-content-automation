# 07 - Handoff Manifest

## Tujuan

Menetapkan kontrak file minimum agar n8n bisa mulai bekerja setelah clip tersedia.

## Aturan utama

1. Python clipper tetap menghasilkan asset secara manual.
2. Job baru hanya boleh masuk ke `shared/ready/` jika semua file final sudah siap.
3. n8n membaca `manifest.json` sebagai entry point utama.

## Struktur folder minimum per job

```text
shared/ready/
└── job_<timestamp>_<shortid>/
    ├── clip_1.mp4
    ├── clip_2.mp4
    ├── transcript.txt
    ├── thumbnail.jpg
    └── manifest.json
```

## Field minimum `manifest.json`

- `job_id`
- `source_video_id`
- `source_video_url`
- `clip_count`
- `clip_path`
- `clips`
- `transcript_path`
- `thumbnail_path`
- `platform_targets`
- `approval_mode`
- `created_at`
- `status`

## Catatan implementasi

- `transcript_path` dan `thumbnail_path` boleh `null` jika asset belum tersedia.
- subtitle adalah bagian dari output generator clip jika fitur subtitle diaktifkan, jadi tidak perlu field manifest terpisah kecuali nanti memang dibutuhkan.
- `clip_path` adalah shortcut ke clip pertama agar alur sederhana di n8n tetap mudah.
- `clips` adalah daftar semua clip hasil satu job agar n8n bisa loop tanpa menebak isi folder.
- penulisan manifest sebaiknya additive melalui helper handoff, bukan dengan mengubah logic inti clipper dulu.
