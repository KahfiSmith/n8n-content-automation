# 10 - Setup TikTok via Zapier

## Tujuan

Mengirim clip siap publish ke TikTok lewat Zapier tanpa memakai TikTok Developer API langsung.

Pendekatan ini sengaja dipilih karena TikTok API resmi butuh proses review app yang lama dan belum tentu disetujui. Untuk MVP lokal, Zapier lebih realistis selama file video bisa diakses Zapier.

## Batasan utama

Zapier berjalan di cloud, jadi Zapier tidak bisa membaca path lokal Docker seperti:

```text
/files/ready/job_xxx/clip_1.mp4
shared/ready/job_xxx/clip_1.mp4
```

Karena itu, payload dari n8n ke Zapier harus berisi URL video yang bisa diakses Zapier, bukan hanya path lokal.

## Arsitektur yang disarankan

```text
Python clipper
  -> shared/ready/<job_id>/
  -> n8n WF-01 intake
  -> n8n WF-02 caption
  -> upload/sync video ke storage publik
  -> n8n WF-04 submit payload ke Zapier
  -> Zapier upload ke TikTok
```

Storage publik untuk MVP bisa salah satu:

- Google Drive folder yang bisa diakses Zapier
- Dropbox
- Cloudflare R2/S3-compatible bucket dengan signed/public URL
- VPS static file endpoint nanti saat pindah dari lokal

## Environment

Tambahkan ke `.env`:

```bash
TIKTOK_ZAPIER_WEBHOOK_URL=
TIKTOK_FILE_BASE_URL=
TIKTOK_ALLOW_SUBMIT_WITHOUT_APPROVAL=true
```

Catatan:

- `TIKTOK_ZAPIER_WEBHOOK_URL` adalah URL dari Zapier Catch Hook.
- `TIKTOK_FILE_BASE_URL` hanya dipakai jika file bisa dipetakan dari path lokal ke URL publik.
- Jika memakai Google Drive trigger langsung, `TIKTOK_FILE_BASE_URL` boleh kosong dan Zapier bisa mengambil file dari Google Drive.

## Payload dari n8n ke Zapier

Minimal payload per clip:

```json
{
  "job_id": "job_20260403_101530_ab12cd",
  "clip_id": "clip_01",
  "clip_index": 1,
  "platform": "tiktok",
  "video_url": "https://example.com/ready/job_xxx/clip_1.mp4",
  "file_name": "clip_1.mp4",
  "caption": "Caption siap upload",
  "hashtags": ["#TikTok", "#ContentCreator"],
  "caption_full": "Caption siap upload #TikTok #ContentCreator",
  "source_video_url": "https://youtube.com/watch?v=xxxx",
  "approval_mode": "required"
}
```

Jika Zapier hanya menerima satu field caption, pakai `caption_full`.

## Setup Zapier

### Opsi A: Webhook dari n8n

Gunakan opsi ini kalau n8n sudah punya `video_url` publik.

1. Buat Zap baru.
2. Trigger: `Webhooks by Zapier` -> `Catch Hook`.
3. Copy webhook URL ke `.env` sebagai `TIKTOK_ZAPIER_WEBHOOK_URL`.
4. Action: TikTok publish/upload video.
5. Map field:
   - video file/url: `video_url`
   - caption: `caption_full`
6. Test dengan satu clip private/draft dulu.

### Opsi B: Google Drive sebagai trigger

Gunakan opsi ini kalau belum punya public file endpoint.

1. Sync/copy clip final ke folder Google Drive khusus TikTok.
2. Zapier trigger: `New File in Folder`.
3. Action berikutnya ambil caption dari metadata sidecar atau webhook n8n.
4. Action TikTok upload video.

Opsi B lebih mudah untuk file upload, tapi mapping caption perlu disiplin naming:

```text
job_xxx_clip_01.mp4
job_xxx_clip_01.json
```

## Marker hasil di repo

Setelah n8n berhasil submit ke Zapier, tulis marker per clip:

```text
shared/ready/<job_id>/tiktok_zapier_result_clip_01.json
```

Status minimum:

- `TIKTOK_ZAPIER_SUBMITTED`
- `TIKTOK_ZAPIER_FAILED`

Jangan langsung tandai `TIKTOK_PUBLISHED` kecuali Zapier mengirim callback atau ada bukti URL publish.

## Rekomendasi MVP

Mulai dari Opsi A jika bisa menyediakan `video_url` publik. Jika belum, mulai dari Opsi B dengan Google Drive karena paling cepat dipakai tanpa membangun API baru.
