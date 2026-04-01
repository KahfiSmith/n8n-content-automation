# 08 - Structure Mapping

## Tujuan

Dokumen ini dipakai sebagai peta struktur repo agar perubahan berikutnya bisa dilakukan dengan aman, konsisten, dan mudah ditinjau.

Gunakan dokumen ini saat:
- ingin menambah folder baru
- ingin memindahkan file
- ingin menambah layer automation
- ingin memastikan perubahan tidak merusak flow existing

## Prinsip perubahan

1. pertahankan folder existing sebanyak mungkin
2. jangan ubah core Python clipper tanpa alasan kuat
3. tambahkan layer baru di sekitar struktur lama
4. gunakan `shared/` sebagai boundary antar domain
5. simpan catatan workflow n8n di `docs/` agar struktur tetap sederhana

## Struktur acuan

```text
project-root/
├── AGENTS.md
├── README.md
├── agents/
├── docs/
├── examples/
├── n8n/
├── python_clipper/
└── shared/
```

## Full Architecture / Structure Folder

```text
project-root/
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── agents/
│   ├── README.md
│   ├── n8n-workflow-engineer.md
│   ├── publisher-ops.md
│   ├── python-integration-guard.md
│   └── solution-architect.md
├── docs/
│   ├── README.md
│   ├── 01-architecture.md
│   ├── 02-workflows.md
│   ├── 03-storage-and-folders.md
│   ├── 04-api-and-integration.md
│   ├── 05-mvp-roadmap.md
│   ├── 06-repo-structure.md
│   ├── 07-handoff-manifest.md
│   └── 08-structure-mapping.md
├── examples/
│   ├── README.md
│   └── clip_manifest.example.json
├── n8n/
│   └── README.md
├── python_clipper/
│   ├── .gitignore
│   ├── LICENSE
│   ├── README.md
│   ├── README_EN.md
│   ├── requirements.txt
│   ├── run.py
│   ├── start.bat
│   ├── webapp.py
│   ├── fonts/
│   ├── images/
│   ├── static/
│   └── templates/
└── shared/
    ├── ready/
    │   └── README.md
    ├── published/
    │   └── README.md
    └── failed/
        └── README.md
```

## Mapping folder ke peran

| Folder | Peran utama | Status | Rule perubahan |
|---|---|---|---|
| `python_clipper/` | manual clip engine | existing, aktif | jangan rename, jangan pindah, jangan ubah import path |
| `shared/ready/` | output final clipper sekaligus handoff ke n8n | existing, aktif | gunakan ini sebagai jalur utama output clip |
| `shared/published/` | hasil publish / selesai | baru, canonical | pakai untuk marker selesai atau arsip publish |
| `shared/failed/` | job gagal | baru, canonical | pakai untuk error handling yang bisa ditelusuri |
| `n8n/` | runtime data n8n lokal | existing, aktif | gunakan hanya untuk runtime dan state lokal instance |
| `docs/` | dokumentasi arsitektur dan kontrak | existing, aktif | semua perubahan struktur sebaiknya dicatat di sini |
| `agents/` | panduan kerja agent | existing, aktif | gunakan untuk guardrail dan peran kerja |
| `examples/` | contoh kontrak data | baru, canonical | simpan contoh manifest dan payload internal di sini |

## Mapping struktur lama ke struktur target

| Struktur lama | Struktur target | Tindakan | Alasan |
|---|---|---|---|
| `python_clipper/` | `python_clipper/` | pertahankan | folder ini sudah jadi pusat logic clipper |
| `python_clipper/clips/` | dihapus | hapus | folder lama kosong dan output aktif sudah pindah ke `shared/ready/` |
| `shared/ready/` | `shared/ready/` | pertahankan | jadi output final clipper dan source utama n8n |
| belum ada `shared/published/` | `shared/published/` | tambah | perlu state selesai publish |
| belum ada `shared/failed/` | `shared/failed/` | tambah | perlu state gagal yang eksplisit |
| `n8n/` | `n8n/` | pertahankan | sudah dipakai sebagai runtime mount Docker |
| belum ada `examples/` | `examples/` | tambah | kontrak data perlu contoh yang mudah dirujuk |

## Folder yang sebaiknya dianggap stabil

Folder berikut sebaiknya dianggap stabil dan tidak dirombak kecuali memang ada keputusan arsitektur baru:

- `python_clipper/`
- `python_clipper/fonts/`
- `python_clipper/images/`
- `python_clipper/static/`
- `python_clipper/templates/`
- `n8n/`
- `agents/`
- `docs/`

## File yang sebaiknya dianggap sensitif

File berikut berdampak langsung ke flow yang sudah berjalan:

- `python_clipper/run.py`
- `python_clipper/webapp.py`
- `python_clipper/start.bat`
- `python_clipper/static/app.js`
- `docker-compose.yml`
- `.env.example`
- `AGENTS.md`

Jika file ini harus diubah:
- lakukan secara additive
- hindari rename
- dokumentasikan dampaknya

## Cara mapping jika ada perubahan baru

Saat ada rencana perubahan, petakan dulu ke tabel ini:

| Jenis perubahan | Lokasi yang benar | Yang harus dicek |
|---|---|---|
| tambah workflow n8n | `docs/` atau export manual di luar runtime | jangan simpan di `n8n/` runtime |
| tambah state handoff | `shared/` | pastikan status folder punya arti yang jelas |
| tambah helper integrasi | dekat `python_clipper/` atau root script util | jangan ubah flow clipper inti bila belum perlu |
| tambah dokumen arsitektur | `docs/` | sinkronkan dengan README bila berdampak besar |
| tambah contoh payload | `examples/` | pastikan konsisten dengan docs manifest |

## Aturan rename

Rename hanya layak dilakukan jika:

1. nama folder sekarang benar-benar menyesatkan
2. ada nilai arsitektural yang jelas
3. dampak terhadap script, import path, dan docs bisa dikendalikan
4. ada rencana migrasi yang jelas

Saat ini rename **tidak diperlukan** untuk:
- `python_clipper/`
- `n8n/`
- `agents/`
- `docs/`

## Aturan tambah folder baru

Sebelum menambah folder baru, cek:

1. apakah peran itu sudah bisa ditampung di folder existing
2. apakah folder baru punya boundary yang jelas
3. apakah folder baru akan dipakai terus, bukan hanya sementara
4. apakah penamaannya sesuai domain, bukan implementasi sesaat

## Checklist sebelum melakukan perubahan struktur

- perubahan ini additive atau destructive
- ada folder existing yang sudah bisa dipakai atau tidak
- ada impact ke Python clipper atau tidak
- ada impact ke Docker Compose atau tidak
- ada impact ke handoff contract atau tidak
- docs mana yang harus ikut diupdate

## Rekomendasi alur perubahan yang aman

1. update dokumen mapping ini dulu jika perubahan struktural cukup besar
2. tambahkan folder atau file baru tanpa menghapus yang lama
3. buat helper atau integrasi baru di layer pinggir
4. verifikasi bahwa flow Python lama tetap hidup
5. baru setelah stabil, evaluasi apakah struktur lama masih perlu dipertahankan

## Keputusan arsitektur saat ini

Keputusan yang berlaku sekarang:

- clip generation tetap manual dari `python_clipper/`
- n8n mulai setelah output clip tersedia
- `shared/ready/` adalah jalur handoff yang disarankan
- `n8n/` tetap untuk runtime lokal
- catatan dan referensi workflow n8n disimpan di `docs/`
- perubahan harus seminimal mungkin
