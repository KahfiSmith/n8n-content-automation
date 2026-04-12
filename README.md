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

## Peran folder utama

### `python_clipper/`
Folder aplikasi clipper manual yang sudah ada. Semua logic Python utama tetap berada di sini.

Catatan:
- hasil generate sekarang diarahkan ke `shared/ready/`
- web UI tetap berjalan, hanya lokasi penyimpanan final clip yang dipindahkan ke area handoff
- durasi final clip sekarang ditargetkan minimal 45 detik dan maksimal 60 detik jika source video memungkinkan, agar tetap aman untuk YouTube Shorts publish

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
