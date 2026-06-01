# n8n Content Automation

Repo ini mempertahankan pola kerja yang sudah ada:

- `python_clipper/` tetap menjadi engine clip manual
- `n8n` baru bekerja setelah output clip tersedia
- handoff dilakukan lewat folder `shared/`
- `docs/` dan `agents/` menjadi panduan kerja, bukan pengganti logic aplikasi

Perubahan di repo ini dibuat konservatif:

- tidak memindahkan file Python existing
- tidak mengubah import path Python
- tidak mengubah flow web UI clipper
- hanya menambahkan layer automation dan dokumentasi di sekitar struktur lama

## Prinsip arsitektur

1. Python clipper tetap source-of-truth untuk pembuatan media.
2. n8n hanya mengorkestrasi tahap setelah asset siap diproses.
3. Handoff antar domain harus eksplisit melalui folder dan manifest.
4. Struktur baru ditambahkan di sekitar struktur lama, bukan menggantikannya.

## Struktur repo saat ini

```text
.
├── AGENTS.md
├── README.md
├── agents/
├── docs/
├── examples/
├── n8n/
├── python_clipper/
├── shared/
│   ├── failed/
│   ├── published/
│   └── ready/
├── docker-compose.yml
└── .env.example
```

## Cara Running Repo

Repo ini jalan dalam dua bagian:

- `python_clipper/` untuk generate clip video secara manual
- `n8n` lewat Docker Compose untuk automation setelah clip siap

### 1. Siapkan environment

Dari root repo:

```bash
cp .env.example .env
```

Isi `.env` sesuai kebutuhan lokal. Minimal pastikan konfigurasi berikut tersedia:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `N8N_HOST`
- `N8N_PROTOCOL`
- `N8N_EDITOR_BASE_URL`
- `WEBHOOK_URL`

Untuk fitur caption AI, isi juga:

- `OPENAI_API_KEY`

Untuk publish YouTube, config OAuth dibaca dari:

```text
shared/config/youtube_oauth.json
```

Field penting di file itu:

- `client_id`
- `client_secret`
- `refresh_token`
- `privacy_status`
- `allow_publish_without_approval`

### 2. Jalankan n8n dan Postgres

Dari root repo:

```bash
docker compose up -d
```

Cek service:

```bash
docker compose ps
```

Buka n8n:

```text
http://localhost:5678
```

Folder `shared/` di host akan terbaca di container n8n sebagai:

```text
/files
```

Contoh mapping penting:

```text
shared/ready/job_id/manifest.json -> /files/ready/job_id/manifest.json
shared/config/youtube_oauth.json -> /files/config/youtube_oauth.json
```

### 3. Jalankan Python clipper

Dari root repo:

```bash
cd python_clipper
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jika ingin memakai subtitle AI lokal:

```bash
python -m pip install faster-whisper
```

Jalankan web app clipper:

```bash
python webapp.py
```

Buka:

```text
http://127.0.0.1:5000
```

Output clip akan dibuat ke:

```text
shared/ready/<job_id>/
```

Minimal output yang harus ada sebelum n8n dipakai:

- `manifest.json`
- `clip_1.mp4`
- `clip_2.mp4` jika ada lebih dari satu clip

### 4. Jalankan workflow n8n

Urutan manual yang direkomendasikan:

1. `WF-01 Intake Clip + Validate Assets`
2. `WF-02 Generate Caption Auto Schedule`
3. `WF-03 Publish YouTube Shorts Auto Schedule`

Workflow TikTok (opsional, lihat `docs/02-workflows.md`):

4. `WF-04 Publish TikTok via Zernio` — publish clip dari pipeline `caption_result.json` ke TikTok
5. `WF-05 Manual GDrive Inbox to TikTok Zernio Draft` — pantau folder GDrive, auto caption, draft TikTok

Catatan:

- `WF-01` membaca job clip di `shared/ready/`
- `WF-02` membuat `caption_result.json` dan CSV upload queue
- `WF-03` publish ke YouTube Shorts memakai `caption_result.json`, `manifest.json`, dan file clip
- `WF-03` menulis result per clip seperti `youtube_publish_result_clip_01.json`
- `WF-04` butuh config `shared/config/zernio_api_key.txt` dan `wf04_gdrive_upload_folder_id` di `shared/config/tiktok_zernio.json`
- `WF-05` butuh config `shared/config/tiktok_zernio.json` (folder inbox + akun Zernio)

Jika workflow belum muncul di n8n, import workflow dari folder:

```text
shared/imports/
```

Contoh import dari container:

```bash
docker compose exec n8n n8n import:workflow --input=/files/imports/wf-01-intake-clip-validate-assets.json
docker compose exec n8n n8n import:workflow --input=/files/imports/wf-02-generate-caption-auto-schedule.json
docker compose exec n8n n8n import:workflow --input=/files/imports/wf-03-publish-youtube-shorts-auto-schedule.json
docker compose exec n8n n8n import:workflow --input=/files/imports/wf-04-publish-tiktok-zernio.json
docker compose exec n8n n8n import:workflow --input=/files/imports/wf-05-manual-gdrive-to-zernio.json
```

### 5. Cek hasil publish YouTube

Setelah `WF-03`, cek file:

```text
shared/ready/<job_id>/youtube_publish_result_clip_01.json
shared/ready/<job_id>/youtube_publish_result_clip_02.json
```

Status yang mungkin muncul:

- `YOUTUBE_UPLOADED`: upload sudah diterima dan processing YouTube selesai
- `YOUTUBE_PROCESSING_PENDING`: upload diterima, tapi YouTube masih processing
- `YOUTUBE_UPLOAD_FAILED`: upload gagal, baca `error_code` dan `error_message`

Untuk cek status processing dari terminal:

```bash
docker compose cp scripts/check_youtube_processing.js n8n:/tmp/check_youtube_processing.js
docker compose exec n8n node /tmp/check_youtube_processing.js --config /files/config/youtube_oauth.json --job-dir /files/ready/<job_id>
```

Jika error `YOUTUBE_UPLOAD_LIMIT_EXCEEDED` muncul, itu berarti YouTube sedang menolak upload tambahan dari akun/channel tersebut. Tunggu limit reset sebelum rerun `WF-03`.

## Peran folder utama

### `python_clipper/`
Folder aplikasi clipper manual yang sudah ada. Semua logic Python utama tetap berada di sini.

Catatan:
- hasil generate sekarang diarahkan ke `shared/ready/`
- web UI tetap berjalan, hanya lokasi penyimpanan final clip yang dipindahkan ke area handoff
- durasi final clip sekarang ditargetkan minimal 45 detik dan maksimal 60 detik jika source video memungkinkan, agar tetap aman untuk YouTube Shorts publish
- jika segment download dari YouTube under-deliver, clipper sekarang fallback ke full download lalu trim lokal agar target durasi tetap tercapai
- export clip sekarang juga meresinkronkan audio; jika segment hasil download mulai dengan audio telat, clipper fallback ke full download lalu trim akurat

### `shared/`
Area handoff antar Python dan automation.

Folder yang dipakai:
- `shared/ready/` untuk job yang sudah final dan siap dibaca n8n
- `shared/published/` untuk job yang sudah selesai publish
- `shared/failed/` untuk job yang gagal validasi atau gagal automation

### `n8n/`
Runtime data directory untuk instance n8n lokal yang dijalankan dari Docker Compose.

Folder ini dipertahankan karena sudah dipakai oleh:
- [docker-compose.yml](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/docker-compose.yml)

### `docs/`
Dokumentasi arsitektur, storage, handoff contract, dan catatan workflow n8n.

### `agents/`
Panduan peran agent saat Codex membantu pengembangan repo ini.

### `examples/`
Contoh file kontrak data seperti `manifest.json`.

## Alur kerja yang direkomendasikan

1. User menjalankan clip generation secara manual dari `python_clipper/`.
2. Hasil akhir langsung disimpan ke area handoff `shared/ready/`.
3. `manifest.json` menjadi kontrak input bagi n8n.
4. Workflow n8n membaca manifest, validasi asset, lalu melanjutkan caption, approval, dan publish.
5. Hasil akhir dipindahkan atau dicatat ke `shared/published/` atau `shared/failed/`.

## Handoff minimal untuk MVP

Satu job idealnya memiliki:

- `clip.mp4`
- `manifest.json`
- `transcript.txt` bila ada
- `thumbnail.jpg` bila ada

Catatan:
- subtitle sudah menjadi bagian dari proses generator clip Python
- n8n tidak memerlukan kontrak JSON terpisah khusus subtitle

Lihat:
- [examples/clip_manifest.example.json](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/examples/clip_manifest.example.json)
- [docs/07-handoff-manifest.md](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/docs/07-handoff-manifest.md)

## Apa yang sengaja tidak diubah

- logic inti di [python_clipper/run.py](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/python_clipper/run.py)
- web flow di [python_clipper/webapp.py](/home/kahfismith/Kahfi/Project/Backend/n8n-content-automation/python_clipper/webapp.py)
- struktur asset di `python_clipper/fonts/`, `python_clipper/images/`, `python_clipper/templates/`, dan `python_clipper/static/`

## Next step yang aman

1. Buat workflow intake n8n pertama yang membaca `manifest.json` dari `shared/ready/`.
2. Loop `clip_path` atau `clips[]` sesuai kebutuhan upload.
3. Jaga semua perubahan Python bersifat additive, bukan refactor besar.
