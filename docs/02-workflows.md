# 02 - Workflows

## Tujuan dokumen
Mendefinisikan workflow n8n modular untuk kasus saat clip sudah tersedia dari folder Python.

---

## Workflow overview

1. `WF-01 Intake Clip + Validate Assets`
2. `WF-02 Generate Caption`
3. `WF-03 Publish YouTube Shorts`

## Future / optional

- Approval Gate
- Publish TikTok
- Publish Facebook Reels
- Finalize
- Error Handler

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
6. jika valid, teruskan ke `WF-02`

### Output
- payload kerja downstream yang sudah dinormalisasi
- `intake_result.json` dengan status `ASSETS_VALID` atau `ASSETS_INVALID`
- `platform_targets` yang sudah siap dipakai untuk branch publish per platform

### Dedupe minimum
- jika folder job sudah punya `intake_result.json`, workflow intake harus skip dan tidak memproses ulang job yang sama

---

## WF-02 Generate Caption

### Tujuan
Menghasilkan caption dan hashtag yang relevan dengan isi clip tanpa output template tambahan yang tidak dipakai publish.

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
- `caption_pack`
- `hashtags`
- `content_angle`

### Status hasil caption
- `CAPTION_GENERATED`
- `CAPTION_FAILED`

### Branch
- AI success → lanjut
- AI invalid JSON → retry sekali dengan prompt fallback
- tetap gagal → tandai `CAPTION_FAILED`

### Catatan kontrak
- output caption tidak lagi menyimpan `title`, `hook_options`, atau `cta_options`
- `caption_pack` hanya perlu menyimpan `platform`, `caption`, dan `hashtags`
- workflow publish `WF-03` boleh menurunkan title upload secara internal dari caption jika platform membutuhkannya
- jika `transcript_path` kosong, `WF-02` sebaiknya tetap memakai `source_video_title`, `source_video_uploader`, dan deskripsi sumber dari `manifest.json` agar caption tidak jatuh ke fallback generik
- `next_stage` default untuk MVP lokal sekarang adalah `WF-03_PUBLISH_YOUTUBE_SHORTS`

---

## WF-03 Publish YouTube Shorts

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
- upload diterima tapi processing belum selesai → tulis status pending lalu tunggu run schedule berikutnya
- processing selesai → ubah visibility ke target final lalu tandai sukses
- transient fail → retry
- auth fail → tulis `YOUTUBE_UPLOAD_FAILED`

### Rule routing
Workflow ini hanya jalan jika `platform_targets` mengandung `youtube_shorts`.

### Catatan title
- `WF-03` boleh membentuk title YouTube secara internal dari kalimat pertama caption jika `WF-02` tidak menyediakan title eksplisit

### Setup minimum
- butuh `shared/config/youtube_oauth.json`
- file itu bisa digenerate dari `.env` dengan `python3 scripts/write_youtube_config.py`
- untuk MVP lokal, `allow_publish_without_approval` boleh `true`
- dedupe minimum: hanya skip jika status existing sudah `YOUTUBE_UPLOADED`
- jika status existing masih `YOUTUBE_PROCESSING_PENDING`, workflow harus lanjut polling status video yang sama, bukan upload ulang

### Output
- `youtube_publish_result.json`
- `video_id`
- `youtube_watch_url`
- `youtube_studio_url`
- `privacy_status`

### Status hasil
- `YOUTUBE_PROCESSING_PENDING`
- `YOUTUBE_UPLOADED`
- `YOUTUBE_UPLOAD_FAILED`

### Catatan visibility
- jika target visibility akhir adalah `public` atau `unlisted`, workflow tetap upload awal sebagai `private`
- setelah YouTube selesai processing, workflow akan mencoba mengubah visibility ke target akhir

---

## Future: Approval Gate

### Tujuan
Jika nanti quality control manual diaktifkan lagi, gate approval diletakkan di antara `WF-02` dan `WF-03`.

Status yang relevan untuk approval tetap:

- `WAITING_APPROVAL`
- `APPROVED`
- `REJECTED`

---

## Future: Publish TikTok

Pisahkan workflow TikTok dari YouTube dan aktifkan hanya jika target platform memang sudah siap.

---

## Future: Publish Facebook Reels

Pisahkan workflow Facebook Reels dari YouTube dan aktifkan hanya jika target platform memang sudah siap.

---

## Future: Finalize & Archive

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

## Future: Error Handler

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
- Publish YouTube sebagai stage ketiga
- Default manifest clipper menargetkan `youtube_shorts`, `tiktok`, dan `facebook_reels`
- Workflow publish tetap harus branch per `platform_targets`, bukan mengasumsikan semua platform selalu aktif

### Next step
- Approval gate opsional di antara `WF-02` dan `WF-03`
- Python helper kirim webhook saat manifest siap
- polling jadi fallback, bukan jalur utama
