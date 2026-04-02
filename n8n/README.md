# n8n Runtime

Folder ini dipertahankan untuk runtime data n8n lokal.

Saat ini folder ini dipakai oleh Docker Compose melalui mount:
- `./n8n:/home/node/.n8n`

Jangan campur file versioned workflow ke sini jika ingin menjaga repo tetap bersih.
Simpan referensi workflow, mapping node, dan panduan integrasi di `docs/`.
