# 02 - Workflows

## Tujuan dokumen
Mendefinisikan workflow n8n modular untuk kasus saat clip sudah tersedia dari folder Python.

---

## Workflow overview

1. `WF-01 Intake Clip + Validate Assets`
2. `WF-02 Generate Caption`
3. `WF-03 Approval Gate`
4. `WF-04 Publish YouTube Shorts`
5. `WF-05 Publish TikTok`
6. `WF-06 Publish Facebook Reels`
7. `WF-07 Finalize`
8. `WF-08 Error Handler`

---

## WF-01 Intake Clip + Validate Assets

### Tujuan
Mengambil clip/job baru yang sudah siap diproses.

### Trigger options
- Cron polling folder
- Webhook dari helper script Python
- Manual trigger dengan path manifest

### Input
- `manifest_path`
- `job_id`
- `clip_id`

### Langkah utama
1. ambil manifest
2. parse JSON
3. cek dedupe berdasarkan `intake_result.json`
4. validasi field wajib
5. set `pipeline_status = INTAKE_RECEIVED`
6. jika valid, teruskan ke WF-02

### Output
- payload kerja downstream yang sudah dinormalisasi
- `intake_result.json` dengan status `ASSETS_VALID` atau `ASSETS_INVALID`
- `platform_targets` yang sudah siap dipakai untuk branch publish per platform

### Dedupe minimum
- jika folder job sudah punya `intake_result.json`, workflow intake harus skip dan tidak memproses ulang job yang sama

---

## WF-02 Generate Caption

### Tujuan
Menghasilkan hook, caption, hashtag, CTA, dan variasi copy dari transcript clip.

### Setup minimum
- isi `OPENAI_API_KEY` dan setting caption lain di `.env`
- jalankan `python3 scripts/write_caption_config.py` untuk membuat `shared/config/caption_ai.json`
- workflow membaca `shared/config/caption_ai.json` lewat mount `/files/config/caption_ai.json`
- model default yang aman untuk MVP: `gpt-5.4-mini`
- file `shared/config/caption_ai.json` bersifat lokal dan di-ignore dari git
- workflow ini sebaiknya hanya memproses job yang sudah punya `intake_result.json` dengan status `ASSETS_VALID`
- dedupe minimum: jika folder job sudah punya `caption_result.json`, skip dan jangan generate ulang

### Input terbaik
- transcript clip
- title sumber
- source url
- niche / brand voice
- platform targets
- approval mode

### Output
- `caption_result.json`
- `title`
- `caption_pack`
- `hook_options`
- `cta_options`
- `hashtags`
- `content_angle`

### Status hasil caption
- `CAPTION_GENERATED`
- `CAPTION_FAILED`

### Branch
- AI success → lanjut
- AI invalid JSON → retry sekali dengan prompt fallback
- tetap gagal → WF-08

### Catatan kontrak
- status approval seperti `WAITING_APPROVAL`, `APPROVED`, dan `REJECTED` tetap milik `WF-03 Approval Gate`, bukan `caption_result.json`
- `caption_pack` sebaiknya sudah berisi copy per platform agar publish workflow tidak perlu menebak teks untuk `youtube_shorts`, `tiktok`, dan `facebook_reels`

---

## WF-03 Approval Gate

### Tujuan
Membuka mode semi-automatic untuk quality control.

### Input
- thumbnail/preview
- transcript summary
- caption usulan
- platform target

### Branch
- approve → lanjut publish
- reject → failed/manual review
- revise → balik ke caption step atau edit manual

### Catatan MVP
Untuk MVP, workflow ini sebaiknya aktif default.

---

## WF-04 Publish YouTube Shorts

### Input
- final video path
- title
- description/caption
- tags/hashtags
- privacy/schedule

### Output
- youtube status
- post/video id
- publish url jika tersedia

### Branch
- success → lanjut
- transient fail → retry
- auth fail → WF-08

### Rule routing
Workflow ini hanya jalan jika `platform_targets` mengandung `youtube_shorts`.

### Setup minimum
- butuh `shared/config/youtube_oauth.json`
- file itu bisa digenerate dari `.env` dengan `python3 scripts/write_youtube_config.py`
- untuk MVP lokal, `allow_publish_without_approval` boleh `true`
- dedupe minimum: jika folder job sudah punya `youtube_publish_result.json`, skip dan jangan upload ulang

### Output
- `youtube_publish_result.json`
- `video_id`
- `youtube_watch_url`
- `youtube_studio_url`
- `privacy_status`

### Status hasil
- `YOUTUBE_UPLOADED`
- `YOUTUBE_UPLOAD_FAILED`

---

## WF-05 Publish TikTok

### Input
- final video path
- caption TikTok
- hashtags
- account target

### Output
- tiktok status
- media/post id

### Catatan
Pisahkan error handling TikTok dari YouTube.

### Rule routing
Workflow ini hanya jalan jika `platform_targets` mengandung `tiktok`.

---

## WF-06 Publish Facebook Reels

### Input
- final video path
- caption Reels
- target page/account

### Output
- facebook status
- media/post id

### Rule routing
Workflow ini hanya jalan jika `platform_targets` mengandung `facebook_reels`.

---

## WF-07 Finalize & Archive

### Tujuan
Menutup job dengan rapi.

### Langkah
1. gabungkan status per platform
2. tentukan final status
3. pindahkan file/job ke `published/` atau beri marker selesai
4. simpan log summary

### Final status example
- `PUBLISHED_ALL`
- `PUBLISHED_PARTIAL`
- `WAITING_APPROVAL`
- `FAILED`

---

## WF-08 Error Handler

### Tujuan
Menangani semua error dengan pola konsisten.

### Input
- stage
- error code
- error detail
- retry count
- manifest context

### Kategori error
- file missing
- transcript missing
- AI invalid output
- auth expired
- upload rejected
- rate limit

### Tindakan
- retry bila transient
- pindah ke `failed/`
- kirim alert
- simpan incident record

---

## Rekomendasi orchestration mode

### MVP
- Intake via polling folder `ready/`
- Caption generation via polling `intake_result.json` yang valid
- Approval aktif
- Default manifest clipper menargetkan `youtube_shorts`, `tiktok`, dan `facebook_reels`
- Workflow publish tetap harus branch per `platform_targets`, bukan mengasumsikan semua platform selalu aktif

### Next step
- Python helper kirim webhook saat manifest siap
- polling jadi fallback, bukan jalur utama
