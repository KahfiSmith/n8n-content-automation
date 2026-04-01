# 02 - Workflows

## Tujuan dokumen
Mendefinisikan workflow n8n modular untuk kasus saat clip sudah tersedia dari folder Python.

---

## Workflow overview

1. `WF-01 Intake Clip`
2. `WF-02 Validate Assets`
3. `WF-03 Generate Caption`
4. `WF-04 Approval Gate`
5. `WF-05 Publish YouTube Shorts`
6. `WF-06 Publish TikTok`
7. `WF-07 Publish Facebook Reels`
8. `WF-08 Finalize`
9. `WF-09 Error Handler`

---

## WF-01 Intake Clip

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
3. validasi field wajib
4. set `pipeline_status = INTAKE_RECEIVED`
5. teruskan ke WF-02

### Output
- payload kerja downstream yang sudah dinormalisasi

---

## WF-02 Validate Assets

### Tujuan
Memastikan semua asset yang dibutuhkan benar-benar ada sebelum AI/publish berjalan.

### Validasi minimal
- file video ada
- ukuran file masuk akal
- transcript path valid bila ada
- thumbnail path valid bila ada
- platform targets ada

### Branch
- valid → WF-03
- invalid → WF-09

### Status
- `VALIDATING_ASSETS`
- `ASSETS_VALID`
- `ASSETS_INVALID`

---

## WF-03 Generate Caption

### Tujuan
Menghasilkan hook, caption, hashtag, CTA, dan variasi copy dari transcript clip.

### Input terbaik
- transcript clip
- title sumber
- source url
- niche / brand voice
- platform targets
- approval mode

### Output
- `caption_pack`
- `hook_options`
- `cta_options`
- `hashtags`
- `content_angle`

### Branch
- AI success → lanjut
- AI invalid JSON → retry sekali dengan prompt fallback
- tetap gagal → WF-09

---

## WF-04 Approval Gate

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

## WF-05 Publish YouTube Shorts

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
- auth fail → WF-09

---

## WF-06 Publish TikTok

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

---

## WF-07 Publish Facebook Reels

### Input
- final video path
- caption Reels
- target page/account

### Output
- facebook status
- media/post id

---

## WF-08 Finalize & Archive

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

## WF-09 Error Handler

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
- Approval aktif
- Publish YouTube dulu
- TikTok/Facebook menyusul

### Next step
- Python helper kirim webhook saat manifest siap
- polling jadi fallback, bukan jalur utama