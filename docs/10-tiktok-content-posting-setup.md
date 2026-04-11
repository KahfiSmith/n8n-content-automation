# 10 - TikTok Content Posting Setup

## Tujuan dokumen
Menyiapkan jalur TikTok sebagai helper opsional tanpa menambah workflow aktif baru di MVP saat ini.

Fokusnya:
- config lokal
- helper CLI
- validasi creator info
- init upload draft atau direct post
- cek status publish TikTok

Dokumen ini sengaja tidak mengaktifkan workflow n8n baru dulu. Jalur TikTok disiapkan sebagai helper terpisah supaya integrasi bisa diuji tanpa merusak alur 3 workflow aktif.

---

## Realitas integrasi TikTok

Untuk TikTok, jalur resminya adalah **Content Posting API**.

Ada dua mode utama:

1. `UPLOAD`
   - upload video ke inbox/draft TikTok
   - creator lanjut edit/post di aplikasi TikTok

2. `DIRECT_POST`
   - post langsung ke profil TikTok
   - scope dan audit lebih ketat

Untuk MVP lokal, mulai dari `UPLOAD` dulu. Jalur ini paling aman untuk testing dan paling sedikit titik gagal.

---

## File yang dipakai

### Env
Isi variabel ini di `.env`:

```bash
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_ACCESS_TOKEN=
TIKTOK_REFRESH_TOKEN=
TIKTOK_OPEN_ID=
TIKTOK_SCOPE=
TIKTOK_REDIRECT_URI=
TIKTOK_POST_MODE=UPLOAD
TIKTOK_SOURCE=FILE_UPLOAD
TIKTOK_PRIVACY_LEVEL=SELF_ONLY
TIKTOK_DISABLE_COMMENT=false
TIKTOK_DISABLE_DUET=false
TIKTOK_DISABLE_STITCH=false
TIKTOK_BRAND_CONTENT_TOGGLE=false
TIKTOK_BRAND_ORGANIC_TOGGLE=false
TIKTOK_IS_AIGC=false
TIKTOK_TITLE_SUFFIX=
```

Catatan keamanan:
- isi `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, dan token hanya di `.env` atau `shared/config/tiktok_posting.json`
- jangan isi credential nyata di `.env.example`
- `shared/config/tiktok_posting.json` sudah masuk `.gitignore`

### Generate config lokal

```bash
python3 scripts/write_tiktok_config.py
```

Hasilnya:

```bash
shared/config/tiktok_posting.json
```

File ini lokal, dibaca helper, dan tidak di-commit.

---

## Helper CLI yang tersedia

Script:

```bash
scripts/tiktok_content_post.py
```

Helper tambahan untuk OAuth:

```bash
scripts/tiktok_oauth.py
```

### 0. Ambil token OAuth

Buat URL login:

```bash
python3 scripts/tiktok_oauth.py auth-url \
  --redirect-uri "https://domain-redirect-anda.example/tiktok/callback"
```

Setelah login, TikTok akan redirect ke URL tersebut dengan query `code=...`. Tukar code menjadi token:

```bash
python3 scripts/tiktok_oauth.py exchange-code \
  --code "<code-dari-callback>" \
  --redirect-uri "https://domain-redirect-anda.example/tiktok/callback"
```

Hasil token disimpan ke:

```bash
shared/config/tiktok_posting.json
```

`access_token` TikTok berlaku singkat. Kalau `refresh_token` tersedia, `scripts/tiktok_content_post.py` akan mencoba refresh otomatis dan menulis token baru ke config lokal.

`redirect_uri` harus HTTPS dan harus sama persis dengan yang terdaftar di TikTok Developer Portal. Kalau sudah diisi sebagai `TIKTOK_REDIRECT_URI`, argumen `--redirect-uri` bisa dihilangkan.

### 1. Cek creator info

```bash
python3 scripts/tiktok_content_post.py creator-info
```

Fungsi:
- validasi `access_token`
- lihat opsi `privacy_level`
- lihat apakah comment/duet/stitch dibatasi

### 2. Upload ke draft / inbox TikTok

Jalur paling mudah dari folder job:

```bash
python3 scripts/tiktok_content_post.py post-job \
  --job-dir shared/ready/<job> \
  --post-mode UPLOAD
```

Perintah ini otomatis membaca:
- `shared/ready/<job>/manifest.json`
- `shared/ready/<job>/caption_result.json`
- `clip_path` dari manifest
- caption TikTok dari `clip_caption_pack` jika ada
- fallback ke `caption_pack` global jika caption per clip belum tersedia

Default output:

```bash
shared/ready/<job>/tiktok_publish_result.json
```

Jika `WF-02 Generate Caption Auto Schedule` yang terbaru sudah di-import ke n8n, CSV queue dibuat otomatis setelah `caption_result.json` sukses.

Output otomatis:

```bash
shared/ready/<job>/upload_queue_tiktok.csv
shared/ready/<job>/upload_queue_youtube_shorts.csv
```

Kalau perlu rebuild manual, jalankan:

```bash
python3 scripts/build_upload_queue.py \
  --job-dir shared/ready/<job> \
  --platform tiktok
```

Output:

```bash
shared/ready/<job>/upload_queue_tiktok.csv
shared/ready/<job>/upload_queue_tiktok.json
```

CSV ini selalu punya satu baris per video di `manifest.clips`. Jika caption masih fallback global, kolom `needs_review` akan bernilai `true`.

Jalur manual kalau ingin override file/title:

```bash
python3 scripts/tiktok_content_post.py post-video \
  --file shared/ready/<job>/clip_1.mp4 \
  --title "Caption ringkas yang sudah siap ke TikTok" \
  --post-mode UPLOAD
```

Fungsi:
- init upload ke TikTok
- upload file lokal per chunk
- cek status awal berdasarkan `publish_id`
- bisa menulis `tiktok_publish_result.json` bila diberi `--result-file`

Contoh dengan output result file:

```bash
python3 scripts/tiktok_content_post.py post-video \
  --file shared/ready/<job>/clip_1.mp4 \
  --title "Caption ringkas yang sudah siap ke TikTok" \
  --post-mode UPLOAD \
  --job-id "<job>" \
  --result-file shared/ready/<job>/tiktok_publish_result.json
```

### 3. Direct post ke profil TikTok

```bash
python3 scripts/tiktok_content_post.py post-video \
  --file shared/ready/<job>/clip_1.mp4 \
  --title "Caption ringkas yang sudah siap ke TikTok" \
  --post-mode DIRECT_POST
```

Catatan:
- gunakan ini hanya kalau app dan akun Anda memang sudah siap untuk direct post
- helper akan cek `privacy_level_options` creator lebih dulu

### 4. Cek status publish

```bash
python3 scripts/tiktok_content_post.py status \
  --publish-id <publish_id>
```

---

## Cara kerja helper

1. baca `shared/config/tiktok_posting.json`
2. refresh `access_token` otomatis kalau hanya `refresh_token` yang tersedia
3. hit endpoint TikTok untuk init upload
4. kalau `FILE_UPLOAD`, kirim file video ke `upload_url`
5. cek status awal pakai `publish_id`
6. cetak JSON hasil ke stdout
7. tulis result file jika argumen `--result-file` diberikan

Untuk `post-job`, helper menulis `tiktok_publish_result.json` ke folder job secara default. Untuk `post-video`, helper hanya menulis result file jika argumen `--result-file` diberikan.

---

## Rekomendasi integrasi ke repo

Jangan aktifkan workflow TikTok sebagai `WF-04` sekarang kalau:
- token masih sering berubah
- app TikTok belum stabil
- posting mode belum diputuskan

Urutan yang lebih aman:

1. test helper CLI dulu
2. pastikan `creator-info` lolos
3. pastikan `UPLOAD` draft lolos
4. baru kalau stabil, sambungkan ke workflow n8n future

---

## Hal yang perlu Anda perhatikan

- `UPLOAD` dan `DIRECT_POST` memakai jalur endpoint berbeda
- helper ini saat ini hanya mendukung `FILE_UPLOAD`
- untuk `PULL_FROM_URL`, domain/URL prefix harus diverifikasi di TikTok
- kalau client TikTok Anda belum diaudit, visibility bisa tetap dibatasi TikTok walau request berhasil
- cap upload dan pending share bisa kena limit user per 24 jam
- TikTok mewajibkan `redirect_uri` OAuth sama persis dengan yang terdaftar di Developer Portal
- untuk direct post, field commercial content (`brand_content_toggle`, `brand_organic_toggle`) ikut dikirim walaupun nilainya `false`

---

## Status yang layak dipakai nanti

Kalau nanti helper ini diikat ke workflow n8n, status minimal yang masuk akal:

- `TIKTOK_UPLOAD_INITIATED`
- `TIKTOK_PROCESSING_PENDING`
- `TIKTOK_UPLOADED`
- `TIKTOK_UPLOAD_FAILED`

---

## Jalur operator paling praktis

1. isi `.env`
2. jalankan `python3 scripts/write_tiktok_config.py`
3. cek `creator-info`
4. test `post-video --post-mode UPLOAD`
5. simpan `publish_id`
6. cek `status`
7. baru putuskan kapan TikTok diikat ke n8n
