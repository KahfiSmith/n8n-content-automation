# 05 - MVP Roadmap

## Tujuan dokumen
Memberi urutan implementasi yang realistis, minim kompleksitas, dan tetap membuka jalan scale-up.

---

## MVP target

MVP yang direkomendasikan:
- user generate clip manual dari Python
- Python output masuk ke folder handoff terstruktur
- n8n membaca manifest
- AI membuat caption
- ada approval
- publish minimal ke YouTube Shorts

---

## Wajib di fase awal

### 1. Standardisasi output Python
Yang wajib ada:
- clip final `.mp4`
- `manifest.json`
- path transcript bila tersedia
- struktur folder konsisten

### 2. Workflow intake n8n
Yang wajib bisa dilakukan:
- mendeteksi job baru
- parse manifest
- validasi asset

### 3. Workflow AI caption
Yang wajib:
- transcript/input metadata masuk ke model
- output JSON valid
- ada fallback retry sederhana

### 4. Approval gate
Untuk MVP, approval sangat direkomendasikan.

### 5. Publish satu platform dulu
Mulai dari platform yang integrasinya paling siap untuk Anda.
Secara umum, YouTube Shorts paling masuk akal jadi target pertama.

---

## Optional di fase MVP

- thumbnail otomatis
- multi-caption variants banyak
- multi-platform publish serentak
- webhook submit manifest
- dashboard monitoring terpisah
- auto lifecycle yang kompleks

---

## Tunda dulu

- object storage
- service API penuh untuk Python
- publisher microservice terpisah
- queue system kompleks
- autoscaling
- analytics performa lintas platform yang mendalam
- full automatic tanpa approval

---

## Roadmap implementasi

## Phase 1 — File contract stabilization
Output:
- struktur folder final
- manifest schema final
- contoh job yang valid

## Phase 2 — n8n intake and validation
Output:
- workflow intake
- duplicate prevention dasar
- asset validation

## Phase 3 — AI packaging
Output:
- hook
- caption per platform
- hashtag
- CTA
- JSON schema output

## Phase 4 — Approval flow
Output:
- manual approve/reject sederhana
- status gate yang jelas

## Phase 5 — Publishing
Output:
- publish YouTube Shorts
- log status publish
- simpan post id/url

## Phase 6 — Expansion
Output:
- TikTok
- Facebook Reels
- webhook integration
- better retries

---

## Recommended success criteria per phase

### Phase 1 selesai jika:
- semua clip job punya manifest yang konsisten
- n8n bisa membaca job tanpa tebak file

### Phase 2 selesai jika:
- job valid bisa lanjut otomatis
- job invalid tertahan dengan alasan jelas

### Phase 3 selesai jika:
- AI output konsisten dalam schema yang sama

### Phase 4 selesai jika:
- Anda bisa approve 1 klik dan workflow lanjut

### Phase 5 selesai jika:
- minimal satu platform bisa publish stabil

---

## Final recommendation

Jangan mengejar full automation dulu.

Target terbaik untuk MVP adalah:
**manual clip generation + automated downstream pipeline**.

Model ini paling sejalan dengan kondisi repo Anda saat ini dan paling hemat effort untuk mulai jalan.
