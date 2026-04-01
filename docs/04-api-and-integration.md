# 04 - API and Integration

## Tujuan dokumen
Menjelaskan opsi integrasi yang realistis antara output Python manual dan n8n.

Dokumen ini sengaja memprioritaskan model yang tidak memaksa Anda membungkus clipper menjadi service penuh sejak awal.

---

## Opsi integrasi

## Opsi A — Folder polling

### Deskripsi
n8n melakukan polling ke folder `shared/ready/` untuk mencari `manifest.json` baru.

### Kelebihan
- paling sederhana
- cocok untuk MVP lokal
- hampir tanpa perubahan di Python

### Kekurangan
- ada delay polling
- perlu mekanisme duplicate prevention
- tidak elegan untuk scale besar

### Kapan dipakai
- MVP lokal
- VPS single machine awal

---

## Opsi B — Webhook submit manifest

### Deskripsi
Setelah Python selesai membuat clip, helper script mengirim POST ke webhook n8n dengan path manifest atau payload manifest.

### Kelebihan
- lebih cepat dari polling
- n8n hanya aktif saat ada job baru
- tetap ringan dibanding microservice penuh

### Kekurangan
- Python perlu helper tambahan
- perlu handling bila webhook gagal

### Rekomendasi
Ini upgrade terbaik setelah MVP polling stabil.

---

## Opsi C — HTTP result endpoint

### Deskripsi
Python atau wrapper ringan expose endpoint result untuk dibaca n8n.

Contoh endpoint:
- `POST /submit-manifest`
- `GET /jobs/{job_id}`
- `GET /files/{job_id}/{name}`

### Kelebihan
- lebih rapi
- cocok untuk host/container terpisah
- mudah migrasi ke VPS

### Kekurangan
- lebih kompleks
- perlu auth/basic security

### Kapan dipakai
- saat integrasi file mulai lebih rumit
- saat n8n dan Python tidak lagi satu host/folder

---

## Opsi D — Object storage

### Deskripsi
Python upload hasil clip ke bucket, lalu n8n mengonsumsi object key atau signed URL.

### Kapan dipakai
- scale-up
- multi-worker
- multi-machine

### Untuk sekarang
Belum wajib untuk MVP.

---

## Rekomendasi berjenjang

### Tahap 1
Folder polling + manifest JSON

### Tahap 2
Folder polling tetap ada, tambah webhook submit manifest

### Tahap 3
Result API atau object storage bila sistem mulai besar

---

## Webhook contract yang disarankan

### Endpoint di n8n
`POST /webhook/clip-ready`

### Payload minimal

```json
{
  "job_id": "job_20260331_213010_a1b2c3",
  "clip_id": "clip_01",
  "manifest_path": "shared/ready/job_20260331_213010_a1b2c3/manifest.json",
  "event": "clip_ready"
}
```

### Response minimal

```json
{
  "accepted": true,
  "received_at": "2026-03-31T21:31:00+07:00"
}
```

---

## Optional helper script role

Bila Anda ingin tetap manual tapi lebih nyaman, tambahkan helper script kecil di Python side yang:
- memastikan file final lengkap
- menulis `manifest.json`
- memindahkan folder job ke `ready/`
- optional POST webhook ke n8n

Itu memberi manfaat besar tanpa harus refactor engine utama.

---

## Security minimum

Jika nanti memakai webhook/API:
- gunakan shared secret sederhana
- whitelist host bila memungkinkan
- log semua request masuk
- jangan expose seluruh folder system ke HTTP tanpa kontrol
