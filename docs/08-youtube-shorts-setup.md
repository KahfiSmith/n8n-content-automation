# 08 - Setup YouTube Shorts

## Tujuan

Menyiapkan auth lokal dan workflow publish YouTube Shorts untuk MVP tanpa memindahkan logic video processing ke n8n.

## Yang perlu disiapkan

1. Google Cloud project
2. YouTube Data API v3 aktif
3. OAuth consent screen
4. OAuth Client ID tipe Web Application
5. Refresh token dengan scope `youtube.upload`

## Credential minimum

Isi `.env` dengan field ini:

```bash
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
YOUTUBE_PRIVACY_STATUS=public
YOUTUBE_CATEGORY_ID=22
YOUTUBE_NOTIFY_SUBSCRIBERS=false
YOUTUBE_SELF_DECLARED_MADE_FOR_KIDS=false
YOUTUBE_ALLOW_PUBLISH_WITHOUT_APPROVAL=true
YOUTUBE_TITLE_SUFFIX=
YOUTUBE_DESCRIPTION_FOOTER=
```

Lalu generate file config lokal:

```bash
python3 scripts/write_youtube_config.py
```

Hasilnya akan membuat:

```text
shared/config/youtube_oauth.json
```

File ini dibaca workflow publish lewat mount Docker `/files/config/youtube_oauth.json`.

## Setup Google yang benar

1. Buat project di Google Cloud
2. Enable `YouTube Data API v3`
3. Buat `OAuth consent screen`
4. Buat `OAuth Client ID` tipe `Web application`
5. Tambahkan redirect URI:
   - `https://developers.google.com/oauthplayground`
6. Dapatkan `refresh_token` dengan scope:
   - `https://www.googleapis.com/auth/youtube.upload`

## Catatan penting

- upload Shorts tetap memakai endpoint upload video YouTube biasa
- video akan dianggap Shorts oleh YouTube jika formatnya memenuhi syarat Shorts
- clipper Python sekarang menargetkan final durasi 45-60 detik per clip jika source video memungkinkan, supaya lebih aman untuk YouTube Shorts
- `YOUTUBE_PRIVACY_STATUS` sekarang dipakai langsung sebagai visibility target upload
- jika Anda mengubah target dari `private` ke `public` atau `unlisted`, rerun `WF-03` akan mencoba mengubah video existing yang masih tertunda ke visibility baru
- `YOUTUBE_ALLOW_PUBLISH_WITHOUT_APPROVAL=true` hanya untuk MVP lokal saat approval gate opsional belum dipakai
- ketika approval workflow sudah jadi, ubah nilai itu ke `false`

## Workflow yang dipakai

Workflow publish YouTube sekarang bernama:

- `WF-03 Publish YouTube Shorts Auto Schedule`

Trigger-nya:

- scan `caption_result.json`
- hanya jalan jika status caption `CAPTION_GENERATED`
- hanya jalan jika `platform_targets` mengandung `youtube_shorts`
- expand `manifest.clips[]` menjadi satu publish item per clip
- memakai file `youtube_publish_result_clip_*.json` per clip sebagai checkpoint dedupe
- jika status existing masih `YOUTUBE_PROCESSING_PENDING`, workflow akan melanjutkan pengecekan processing video yang sama dan mencoba menyamakan visibility dengan target terbaru, bukan upload ulang clip baru

## Artefak hasil

Jika upload berhasil:

```text
shared/ready/job_xxx/youtube_publish_result_clip_01.json
shared/ready/job_xxx/youtube_publish_result_clip_02.json
...
```

Status minimum:

- `YOUTUBE_PROCESSING_PENDING`
- `YOUTUBE_UPLOADED`
- `YOUTUBE_UPLOAD_FAILED`

Field bantu debugging yang penting:

- `status_checked_at` untuk melihat kapan poll status terakhir dijalankan
- `publish_mode` untuk membedakan `new_upload`, `reconcile_existing_video`, atau hasil reconcile dari pencarian channel
- `processing_status_source` untuk melihat apakah status final diambil dari `processingDetails.processingStatus` atau fallback `status.uploadStatus`
- `youtube_shorts_url` untuk buka clip langsung di player Shorts

## Cek processing tanpa buka Studio terus-menerus

Untuk cek status per clip dari terminal, pakai helper ini:

```bash
docker compose cp scripts/check_youtube_processing.js n8n:/tmp/check_youtube_processing.js
docker compose exec n8n node /tmp/check_youtube_processing.js --config /files/config/youtube_oauth.json --job-dir /files/ready/<job_id>
```

Jika output masih menunjukkan:

```text
PROCESSING_NO_DURATION ... upload=uploaded processing=processing duration=P0D
```

setelah 30-60 menit, kemungkinan video stuck di sisi YouTube dan perlu dihapus lalu di-upload ulang setelah limit/channel sudah normal.
