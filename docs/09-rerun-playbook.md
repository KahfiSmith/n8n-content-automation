# 09 - Rerun Playbook

## Tujuan

Menyederhanakan cara mengulang proses dari awal tanpa bentrok dengan dedupe n8n.

## Prinsip utama

1. jangan hapus `manifest.json`
2. jangan hapus file clip kecuali memang mau regenerate media
3. hapus hanya artefak hasil stage yang ingin diulang
4. untuk test workflow, manual run lebih aman daripada langsung mengandalkan cron

## Artefak per stage

Untuk satu job di `shared/ready/<job_id>/`, artefak yang dipakai dedupe adalah:

- `intake_result.json`
- `caption_result.json`
- `youtube_publish_result.json`

## Rerun paling aman untuk job yang sama

### Ulang dari intake

Hapus:

- `intake_result.json`
- `caption_result.json`
- `youtube_publish_result.json`

Biarkan:

- `manifest.json`
- file clip `.mp4`
- transcript/thumbnail jika ada

Lalu run urut:

1. `WF-01 Intake Clip + Validate Assets`
2. `WF-02 Generate Caption Auto Schedule`
3. `WF-03 Publish YouTube Shorts Auto Schedule`

### Ulang dari caption

Hapus:

- `caption_result.json`
- `youtube_publish_result.json`

Lalu run:

1. `WF-02 Generate Caption Auto Schedule`
2. `WF-03 Publish YouTube Shorts Auto Schedule`

### Ulang dari publish YouTube saja

Hapus:

- `youtube_publish_result.json`

Lalu run:

1. `WF-03 Publish YouTube Shorts Auto Schedule`

## Urutan manual run yang direkomendasikan

1. refresh tab n8n
2. buka workflow dari daftar workflow, jangan dari draft lama yang sudah lama terbuka
3. jalankan satu workflow dulu
4. cek file result yang ditulis ke folder job
5. baru lanjut ke workflow berikutnya

## Indikator sukses per stage

### Intake

- file `intake_result.json` ada
- status `ASSETS_VALID`

### Caption

- file `caption_result.json` ada
- status `CAPTION_GENERATED`

### Publish YouTube

- file `youtube_publish_result.json` ada
- status `YOUTUBE_UPLOADED`

## Catatan cron

- cron cocok untuk job baru
- untuk debugging, manual run tetap lebih aman
- kalau workflow terlihat skip, cek dulu apakah file result stage itu sudah ada

## Catatan khusus YouTube

- upload sukses tidak selalu berarti video langsung `processed`
- cek `processingStatus` di YouTube Studio atau API jika visibility terasa tertunda
