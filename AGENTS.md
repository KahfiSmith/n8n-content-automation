# AGENTS.md

Dokumen ini adalah aturan kerja global untuk Codex saat membantu mengembangkan repo automation ini.

## Mission

Bangun sistem automation short-form content yang:
- realistis untuk creator automation
- modular
- mudah dipindah dari lokal ke VPS
- menjaga pembagian kerja yang jelas antara Python clip output dan n8n orchestration

## Current System Reality

Arsitektur saat ini **bukan** full auto clip generation via n8n.

Kondisi nyata:
1. User sudah punya folder Python yang bisa menghasilkan clip video.
2. Proses generate clip masih dijalankan manual oleh user.
3. n8n baru bergerak setelah hasil clip tersedia.
4. Fokus utama repo ini adalah automation sesudah clip siap:
   - intake clip metadata
   - AI captioning
   - approval
   - upload/publish
   - logging dan status tracking

Codex harus menghormati kondisi ini dan **tidak memaksa** refactor besar ke microservice penuh kecuali diminta secara eksplisit.

## Primary Architecture Rules

1. **Python clip generation tetap source-of-truth untuk output media**
2. **n8n hanya mengorkestrasi tahapan sesudah clip tersedia**
3. **Manifest JSON adalah kontrak utama antar komponen**
4. **Jangan simpan logika berat video processing di n8n**
5. **Pisahkan concern per modul**
6. **Gunakan file path dan naming yang deterministik**
7. **Semua perubahan harus tetap bisa jalan di MVP lokal**

## What Codex Should Optimize For

Saat membuat file, workflow, helper script, atau refactor:

- utamakan implementasi yang cepat dipakai
- minim manual handoff tambahan
- mudah dipahami user non-enterprise
- mudah di-debug
- bisa berkembang ke webhook/API atau object storage nanti
- tidak over-engineered

## Non-goals For Now

Jangan memprioritaskan hal berikut kecuali diminta:
- distributed queue yang kompleks
- autoscaling worker
- object storage sebagai syarat wajib MVP
- event bus
- observability stack enterprise
- publisher microservice terpisah
- refactor total Python clipper menjadi platform besar

## Required Contracts

Jika Codex membuat atau mengubah alur antar komponen, pastikan ada kontrak berikut:

### 1. Clip Manifest
Setiap clip/job sebaiknya punya metadata minimum:
- `job_id`
- `source_video_url` atau `source_video_id`
- `clip_id`
- `clip_path`
- `transcript_path` atau `transcript_text`
- `thumbnail_path` jika ada
- `status`
- `created_at`

### 2. Publish Job Contract
Untuk masuk ke workflow publish, payload minimal:
- `job_id`
- `clip_id`
- `platform_targets`
- `caption_pack`
- `approval_mode`
- `file_location`

### 3. Status Model
Pisahkan minimal dua domain status:
- `clip_status`
- `publish_status`

## Folder Assumptions

Jika tidak ada struktur lain yang lebih resmi, gunakan asumsi:

```bash
shared/
├── ready/
├── published/
└── failed/
```

- `ready/` → clip + manifest siap dibaca n8n
- `published/` → selesai dipublish atau ditandai selesai
- `failed/` → gagal validasi atau gagal workflow

## How Codex Should Handle Requests

### Saat diminta menulis code
- tulis yang paling sedikit tapi stabil
- jaga backward compatibility sebisa mungkin
- dokumentasikan input/output file dengan jelas

### Saat diminta menulis workflow n8n
- pecah modular, jangan satu workflow raksasa
- gunakan nama node yang deskriptif
- pisahkan retry branch dan error branch

### Saat diminta menulis docs
- hubungkan docs dengan kondisi sistem saat ini
- jelaskan mana yang sudah ada, mana target berikutnya
- bedakan MVP vs future architecture

### Saat diminta membuat API
- buat opsional, bukan hard dependency untuk MVP
- desain API harus kompatibel dengan model folder-manifest lebih dulu

## Decision Preference Order

Jika ada beberapa opsi desain, pilih urutan preferensi ini:

1. paling mudah dijalankan lokal
2. paling sedikit titik gagal
3. paling mudah dipahami dan dirawat
4. paling mudah dinaikkan ke VPS
5. paling mudah diskalakan nanti

## Style Rules For Generated Docs

- Bahasa Indonesia
- profesional tapi praktis
- tidak terlalu teoritis
- gunakan heading yang jelas
- berikan checklist atau tabel hanya bila membantu
- selalu jelaskan asumsi teknis

## Absolute Guardrails

Codex tidak boleh:
- memindahkan seluruh logika video processing ke n8n
- mengasumsikan proses clip sudah full otomatis padahal belum
- menghapus konsep approval untuk MVP tanpa alasan kuat
- mencampur status clip generation dengan status publish menjadi satu field tunggal tanpa konteks
- membuat dependency cloud berbayar sebagai default MVP

## Future Migration Path

Kalau nanti diminta scale-up, arah migrasi yang diperbolehkan:

1. folder watcher → webhook submit
2. local path → HTTP file endpoint
3. local storage → S3/MinIO/R2
4. manual clip trigger → Python service/API
5. n8n direct publish → publisher abstraction

Selama belum diminta, tetap prioritaskan model sederhana.
