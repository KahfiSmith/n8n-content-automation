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
- `source_video_title`
- `source_video_uploader`
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
- `source_video_title`, `source_video_uploader`, `source_video_duration`, dan `source_video_description` sangat disarankan agar workflow caption tetap punya konteks saat transcript kosong.
- subtitle adalah bagian dari output generator clip jika fitur subtitle diaktifkan, jadi tidak perlu field manifest terpisah kecuali nanti memang dibutuhkan.
- `clip_path` adalah shortcut ke clip pertama agar alur sederhana di n8n tetap mudah.
- `clips` adalah daftar semua clip hasil satu job agar n8n bisa loop tanpa menebak isi folder.
- jika UI Python tidak mengirim `platform_targets`, helper manifest default ke `["youtube_shorts", "tiktok", "facebook_reels"]` agar konsisten dengan target publish MVP lintas platform.
- penulisan manifest sebaiknya additive melalui helper handoff, bukan dengan mengubah logic inti clipper dulu.

## File hasil intake yang direkomendasikan

Setelah n8n selesai membaca dan memvalidasi `manifest.json`, workflow intake sebaiknya menulis file status terpisah:

```text
shared/ready/
└── job_<timestamp>_<shortid>/
    ├── manifest.json
    └── intake_result.json
```

Tujuannya:
- memberi penanda eksplisit bahwa job sudah pernah diproses intake
- memudahkan tracking tanpa harus buka execution history n8n
- menyimpan alasan valid / invalid langsung di folder job

Field minimum `intake_result.json`:
- `job_id`
- `stage`
- `status`
- `checked_at`
- `manifest_path`
- `clip_path`
- `validation_errors`

Status yang direkomendasikan:
- `ASSETS_VALID`
- `ASSETS_INVALID`

Contoh:
- [examples/intake_result.example.json](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/examples/intake_result.example.json)

## File hasil caption yang direkomendasikan

Setelah workflow caption selesai, job sebaiknya memiliki artefak status kedua:

```text
shared/ready/
└── job_<timestamp>_<shortid>/
    ├── manifest.json
    ├── intake_result.json
    └── caption_result.json
```

Tujuannya:
- memberi penanda eksplisit bahwa caption sudah pernah digenerate
- memudahkan dedupe workflow `WF-02 Generate Caption`
- menyimpan output copy tanpa harus buka execution history n8n

Field minimum `caption_result.json`:
- `job_id`
- `stage`
- `status`
- `generated_at`
- `manifest_path`
- `platform_targets`
- `approval_mode`
- `caption_pack`
- `hashtags`

Status yang direkomendasikan:
- `CAPTION_GENERATED`
- `CAPTION_FAILED`

Catatan:
- `caption_pack` sebaiknya berisi copy per platform, bukan satu caption generik untuk semua channel
- output caption tidak lagi perlu menyimpan `title`, `hook_options`, `cta_options`, atau `cta` per platform
- field minimum per item `caption_pack` sebaiknya hanya `platform`, `caption`, dan `hashtags`
- status approval tetap dipisah ke `approval_result.json`, jangan dicampur ke file caption

Contoh:
- [examples/caption_result.example.json](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/examples/caption_result.example.json)

## File hasil publish YouTube yang direkomendasikan

Setelah workflow publish YouTube selesai, job sebaiknya memiliki artefak status ketiga:

```text
shared/ready/
└── job_<timestamp>_<shortid>/
    ├── manifest.json
    ├── intake_result.json
    ├── caption_result.json
    └── youtube_publish_result.json
```

Tujuannya:
- memberi penanda eksplisit bahwa upload YouTube sudah pernah dijalankan
- memudahkan dedupe workflow `WF-03 Publish YouTube Shorts`
- menyimpan `video_id` dan URL hasil upload tanpa buka execution history n8n

Field minimum `youtube_publish_result.json`:
- `job_id`
- `stage`
- `status`
- `published_at`
- `manifest_path`
- `caption_result_path`
- `youtube_publish_result_path`
- `clip_path`
- `platform`
- `privacy_status`
- `video_id`
- `youtube_watch_url`
- `youtube_studio_url`

Status yang direkomendasikan:
- `YOUTUBE_UPLOADED`
- `YOUTUBE_UPLOAD_FAILED`

Contoh:
- [examples/youtube_publish_result.example.json](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/examples/youtube_publish_result.example.json)
