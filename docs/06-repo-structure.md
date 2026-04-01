# 06 - Repo Structure

## Tujuan

Menjelaskan struktur repo aktual yang dipakai sekarang dengan perubahan seminimal mungkin.

## Struktur inti

```text
project-root/
├── agents/
├── docs/
├── examples/
├── n8n/
├── python_clipper/
└── shared/
```

## Penjelasan

### `python_clipper/`
Engine clip manual yang sudah berjalan. Folder ini tidak dipindah dan tidak dirombak.

### `n8n/`
Folder runtime data n8n lokal. Digunakan oleh Docker Compose saat n8n dijalankan secara lokal.
Catatan workflow dan integrasi n8n yang ingin disimpan di Git sebaiknya didokumentasikan di `docs/`.

### `shared/`
Layer handoff antar Python dan automation.

State minimal yang dipakai:
- `ready/`
- `published/`
- `failed/`

Folder lama yang masih dipertahankan:
- `input/`
- `output/`
- `temp/`

## Prinsip perubahan

1. jangan pindahkan file Python existing
2. jangan ubah import path
3. tambah struktur baru di sekitar struktur lama
4. gunakan folder existing jika masih masuk akal
5. tambahkan folder baru hanya jika memang dibutuhkan oleh pipeline
