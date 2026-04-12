#!/usr/bin/env node
/* Check YouTube processing status for uploaded Shorts.
 *
 * Usage:
 *   node scripts/check_youtube_processing.js --job-dir shared/ready/<job_id>
 *   node scripts/check_youtube_processing.js --ids id1,id2,id3
 */

const fs = require("fs");
const https = require("https");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");

function parseArgs(argv) {
  const args = {
    config: "shared/config/youtube_oauth.json",
    jobDir: "",
    ids: "",
    json: false,
  };

  for (let index = 2; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--json") {
      args.json = true;
      continue;
    }
    if (arg === "--config" || arg === "--job-dir" || arg === "--ids") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error(`Argumen ${arg} butuh value.`);
      }
      index += 1;
      if (arg === "--config") args.config = value;
      if (arg === "--job-dir") args.jobDir = value;
      if (arg === "--ids") args.ids = value;
      continue;
    }
    throw new Error(`Argumen tidak dikenal: ${arg}`);
  }

  return args;
}

function resolveRepoPath(value) {
  const normalized = String(value || "").replace(/\\/g, "/").replace(/^\.\//, "");
  if (path.isAbsolute(normalized)) return normalized;
  return path.join(ROOT, normalized);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function collectIds(args) {
  if (args.ids) {
    return args.ids
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  if (!args.jobDir) {
    throw new Error("Pakai --job-dir shared/ready/<job_id> atau --ids id1,id2.");
  }

  const jobDir = resolveRepoPath(args.jobDir);
  const files = fs
    .readdirSync(jobDir)
    .filter((name) => /^youtube_publish_result.*\.json$/.test(name))
    .sort();

  const ids = [];
  for (const fileName of files) {
    const payload = readJson(path.join(jobDir, fileName));
    const videoId = String(payload.video_id || "").trim();
    if (videoId) ids.push(videoId);
  }

  return Array.from(new Set(ids));
}

function request(options, body = "") {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => {
        data += chunk;
      });
      res.on("end", () => {
        resolve({ status: res.statusCode, body: data });
      });
    });
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

async function getAccessToken(config) {
  const body = [
    `client_id=${encodeURIComponent(String(config.client_id || ""))}`,
    `client_secret=${encodeURIComponent(String(config.client_secret || ""))}`,
    `refresh_token=${encodeURIComponent(String(config.refresh_token || ""))}`,
    "grant_type=refresh_token",
  ].join("&");

  const response = await request(
    {
      method: "POST",
      hostname: "oauth2.googleapis.com",
      path: "/token",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": Buffer.byteLength(body),
      },
    },
    body,
  );

  const parsed = JSON.parse(response.body || "{}");
  if (response.status >= 400 || !parsed.access_token) {
    throw new Error(`Gagal ambil Google access_token: ${response.status} ${response.body}`);
  }
  return parsed.access_token;
}

async function getVideoStates(accessToken, ids) {
  const response = await request({
    method: "GET",
    hostname: "www.googleapis.com",
    path:
      "/youtube/v3/videos?part=id,snippet,status,processingDetails,contentDetails&id=" +
      ids.map((id) => encodeURIComponent(id)).join(","),
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  const parsed = JSON.parse(response.body || "{}");
  if (response.status >= 400) {
    throw new Error(`Gagal cek YouTube videos.list: ${response.status} ${response.body}`);
  }
  return Array.isArray(parsed.items) ? parsed.items : [];
}

function classify(item) {
  const uploadStatus = item.status?.uploadStatus || "";
  const processingStatus = item.processingDetails?.processingStatus || "";
  const duration = item.contentDetails?.duration || "";

  if (uploadStatus === "processed" || processingStatus === "succeeded") {
    return "READY";
  }
  if (["failed", "rejected", "deleted"].includes(uploadStatus) || ["failed", "terminated"].includes(processingStatus)) {
    return "FAILED";
  }
  if (uploadStatus === "uploaded" && processingStatus === "processing" && duration === "P0D") {
    return "PROCESSING_NO_DURATION";
  }
  return "PROCESSING";
}

function printTable(rows) {
  const headers = ["state", "id", "privacy", "upload", "processing", "duration", "shorts_url"];
  console.log(headers.join("\t"));
  for (const row of rows) {
    console.log(
      [
        row.state,
        row.id,
        row.privacyStatus,
        row.uploadStatus,
        row.processingStatus,
        row.duration,
        row.shortsUrl,
      ].join("\t"),
    );
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const config = readJson(resolveRepoPath(args.config));
  const ids = collectIds(args);
  if (ids.length === 0) {
    throw new Error("Tidak ada video_id yang bisa dicek.");
  }

  const accessToken = await getAccessToken(config);
  const items = await getVideoStates(accessToken, ids);
  const foundIds = new Set(items.map((item) => item.id));
  const rows = items.map((item) => ({
    state: classify(item),
    id: item.id,
    title: item.snippet?.title || "",
    privacyStatus: item.status?.privacyStatus || "",
    uploadStatus: item.status?.uploadStatus || "",
    processingStatus: item.processingDetails?.processingStatus || "",
    failureReason: item.status?.failureReason || item.status?.rejectionReason || item.processingDetails?.processingFailureReason || "",
    duration: item.contentDetails?.duration || "",
    shortsUrl: `https://www.youtube.com/shorts/${item.id}`,
    watchUrl: `https://www.youtube.com/watch?v=${item.id}`,
  }));

  for (const id of ids) {
    if (!foundIds.has(id)) {
      rows.push({
        state: "NOT_FOUND",
        id,
        title: "",
        privacyStatus: "",
        uploadStatus: "",
        processingStatus: "",
        failureReason: "Video ID tidak ditemukan oleh credential YouTube ini.",
        duration: "",
        shortsUrl: `https://www.youtube.com/shorts/${id}`,
        watchUrl: `https://www.youtube.com/watch?v=${id}`,
      });
    }
  }

  if (args.json) {
    console.log(JSON.stringify({ checked_at: new Date().toISOString(), rows }, null, 2));
    return;
  }

  printTable(rows);
  const stuck = rows.filter((row) => row.state === "PROCESSING_NO_DURATION");
  if (stuck.length > 0) {
    console.log("");
    console.log(
      `Catatan: ${stuck.length} video masih processing tanpa durasi (P0D). Kalau tetap begini >30-60 menit, kemungkinan stuck di sisi YouTube.`,
    );
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
