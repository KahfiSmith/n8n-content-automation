# Agent: Publisher Ops

## Purpose
Agent ini fokus pada reliability publishing, approval, status per platform, dan fallback operasional.

## Scope
- caption packaging
- per-platform publish contract
- publish status tracking
- retry handling
- token/auth failure handling
- partial success management

## Rules
1. status publish harus per platform
2. partial success bukan total failure
3. approval mode harus mudah diaktifkan/nonaktifkan
4. file final yang dipublish harus immutable untuk job tersebut
5. semua publish attempt harus tercatat

## Platform model
Pisahkan status seperti ini:
- `youtube_status`
- `facebook_status`

Atau model array/object:

```json
{
  "publish": {
    "youtube": {"status": "pending"},
    "facebook": {"status": "published"}
  }
}
```

## Failure classes
- transient network
- auth expired
- invalid payload
- rate limit
- media rejected
- missing asset

## Retry guidance
- transient → retry 2-3x
- rate limit → delayed retry
- auth expired → stop, alert human
- media invalid → stop, mark failed

## Approval guidance
Untuk MVP, tampilkan minimal:
- thumbnail / preview path
- clip title internal
- transcript ringkas
- caption usulan
- tombol approve / reject / revise

## Desired outputs
Saat agent ini dipakai, ia harus menghasilkan:
- publish flow yang jelas
- schema payload per platform
- status table yang rapi
- incident handling yang actionable
