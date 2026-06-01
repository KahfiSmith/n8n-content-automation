# Shared Handoff Storage

Folder ini adalah batas kerja antara Python clipper dan automation.

Prinsip:
- Python tetap menghasilkan asset
- n8n mulai bekerja setelah asset final tersedia
- manifest menjadi kontrak utama

Folder baru ditambahkan secara konservatif tanpa menghapus folder lama.

## WF-05 Manual Google Drive Inbox

WF-05 adalah jalur alternatif untuk video MP4 yang di-upload manual ke Google Drive
dan tidak berasal dari Python clipper.

Setup:

1. Buat folder Google Drive khusus inbox manual.
2. Salin `config/tiktok_zernio.example.json` menjadi
   `config/tiktok_zernio.json`.
3. Isi `manual_drive_inbox_folder_id` dengan ID folder inbox tersebut.
4. Import `imports/wf-05-manual-gdrive-to-zernio.json`, lalu aktifkan workflow.

Workflow polling folder setiap 5 menit, memproses file dengan MIME `video/mp4`,
membuat caption TikTok dari nama file dan deskripsi Drive, membuat draft Zernio,
dan menyimpan guard idempotency di `state/wf05_manual_gdrive_processed.json`.

Gunakan nama file yang deskriptif atau isi `default_content_context`. WF-05 tidak
menganalisis isi audio atau frame video.
