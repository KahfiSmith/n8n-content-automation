# 01 - Architecture

## Tujuan dokumen
Dokumen ini menjelaskan arsitektur yang paling realistis untuk kondisi Anda saat ini:

- folder Python sudah bisa menampilkan / menghasilkan clip video
- generate clip masih manual oleh user
- n8n baru bergerak sesudah clip siap

Arsitektur ini sengaja **bukan** full automation dari awal, supaya implementasi cepat dan tetap rapi.

---

## Prinsip utama

### 1. Clip generation dipisahkan dari content automation
Clip generation adalah domain Python.

Content automation setelah clip tersedia adalah domain n8n.

### 2. Handover antar domain harus eksplisit
Handover terbaik dilakukan lewat:
- folder output yang konsisten
- manifest JSON
- status folder yang jelas

### 3. n8n hanya memproses asset yang sudah final
n8n tidak boleh membaca file mentah yang belum final render.

### 4. Setiap clip/job punya identitas sendiri
Jangan mengandalkan nama file acak. Selalu gunakan:
- `job_id`
- `clip_id`
- `source_video_id` atau sumber video

---

## Komponen sistem

## A. Python Clipper Workspace
Tanggung jawab:
- user menjalankan clip generation manual
- menghasilkan asset final
- menaruh asset final di folder `shared/ready/`
- subtitle tetap ditangani di layer Python jika fitur subtitle diaktifkan

Output minimal:
- clip `.mp4`
- `manifest.json`
- transcript `.txt` bila ada
- thumbnail `.jpg` bila ada

## B. Shared Storage Layer
Tanggung jawab:
- menjadi area handoff antara Python dan n8n
- menjaga state file secara sederhana

State folder yang disarankan:
- `ready/`
- `published/`
- `failed/`

## C. n8n Orchestrator
Tanggung jawab:
- deteksi clip siap proses
- validasi manifest dan file
- panggil AI caption
- approval optional
- upload ke platform
- update status dan log

## D. AI Caption Layer
Tanggung jawab:
- membuat hook
- caption per platform
- hashtag
- CTA
- variasi copy
- menjaga tone tetap konsisten

## E. Publisher Layer
Untuk MVP bisa berupa workflow n8n langsung.

Tanggung jawab:
- upload asset ke platform target
- mencatat hasil publish
- menangani token, retry, dan partial failure

---

## Diagram alur konseptual

```text
User
  -> Python folder / script manual
  -> output clip + manifest ke shared/ready/
  -> n8n intake workflow
  -> validation
  -> AI caption
  -> approval optional
  -> publish per platform
  -> published / failed
```

---

## Kenapa model ini cocok untuk MVP

Karena model ini:
- cepat diimplementasikan
- tidak memaksa refactor Python besar-besaran
- meminimalkan titik gagal baru
- cukup rapi untuk dipindah ke VPS nanti
- bisa ditingkatkan ke webhook/API setelah alur dasar stabil

---

## Evolusi arsitektur yang direkomendasikan

### Fase 1 — sekarang
- manual Python output
- shared folder handoff
- n8n automation pasca-clip

### Fase 2 — setelah stabil
- Python menulis manifest + optional webhook ke n8n
- n8n tidak perlu polling terlalu sering

### Fase 3 — scale-up
- Python dibungkus service/API
- output masuk ke object storage
- n8n membaca result endpoint atau signed URL

Dokumen ini mengikuti arah desain modular yang sebelumnya Anda minta: pembagian tanggung jawab yang tegas antara clip generation, orchestration, captioning, publishing, logging, dan storage flow. fileciteturn3file0 fileciteturn3file2
