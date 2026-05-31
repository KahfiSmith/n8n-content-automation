import os
import re
import json
import sys
import glob
import subprocess
import requests
import shutil
from urllib.parse import urlparse, parse_qs
import argparse
import warnings
warnings.filterwarnings("ignore")

try:
    from . import manifest_helper
except ImportError:
    import manifest_helper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DEFAULT_READY_DIR = os.path.join(PROJECT_ROOT, "shared", "ready")

OUTPUT_DIR = DEFAULT_READY_DIR      # Directory where generated clips will be saved
MAX_DURATION = 60         # Maximum final duration (in seconds) for each exported clip
MIN_CLIP_DURATION = 45    # Minimum final duration target (in seconds) for each exported clip
MIN_SCORE = 0.40          # Minimum heatmap intensity score to be considered viral
MAX_CLIPS = 10            # Maximum number of clips to generate per video
MAX_WORKERS = 1           # Number of parallel workers (reserved for future concurrency)
PADDING = 10              # Extra seconds added before and after each detected segment
TOP_HEIGHT = 960          # Height for top section (center content) in split mode
BOTTOM_HEIGHT = 320       # Height for bottom section (facecam) in split mode
USE_SUBTITLE = True       # Enable auto subtitle using Faster-Whisper (4-5x faster)
WHISPER_MODEL = "small"    # Whisper model size: tiny, base, small, medium, large
WHISPER_LANGUAGE = None    # Whisper language code (e.g., "id", "en"). None = auto-detect
SUBTITLE_FONT = "Arial"
SUBTITLE_FONTS_DIR = None
SUBTITLE_LOCATION = "bottom"
SUBTITLE_OUTLINE = 1        # Outline thickness in pixels (0 = no outline)
SUBTITLE_SHADOW = 0         # Shadow depth in pixels (0 = no shadow)
YTDLP_COOKIES = None        # Path to YouTube cookies file (Netscape format)
OUTPUT_RATIO = "9:16"
OUT_WIDTH = 1080
OUT_HEIGHT = 1920
LIGHTWEIGHT_EXPORT = False
LIGHTWEIGHT_WIDTH = 540
LIGHTWEIGHT_HEIGHT = 960

_AVAILABLE_ENCODERS = None
SEGMENT_DURATION_TOLERANCE = 3.0
AUDIO_START_TOLERANCE = 0.15
ALWAYS_FULL_DOWNLOAD_TRIM = False


def emit_log(message, log_hook=None):
    print(message)
    if callable(log_hook):
        try:
            log_hook(message)
        except Exception:
            pass


def resolve_clip_window(start_original, source_duration, total_duration):
    """
    Build the final export window for a clip.

    Rules:
    - keep the selected heatmap/custom segment inside the final window
    - prefer adding symmetric context via PADDING
    - target a final duration of at least MIN_CLIP_DURATION when source allows
    - never exceed MAX_DURATION or the source video duration
    """
    source_duration = max(0.0, float(source_duration))
    total_duration = max(0.0, float(total_duration))
    start_original = max(0.0, float(start_original))
    end_original = min(start_original + source_duration, total_duration)

    start = max(0.0, start_original - PADDING)
    end = min(total_duration, end_original + PADDING)
    current_duration = max(0.0, end - start)

    target_duration = min(
        total_duration,
        float(MAX_DURATION),
        max(float(MIN_CLIP_DURATION), current_duration),
    )

    if current_duration > target_duration:
        marker_center = (start_original + end_original) / 2.0
        half_target = target_duration / 2.0
        start = max(0.0, marker_center - half_target)
        end = min(total_duration, start + target_duration)
        start = max(0.0, end - target_duration)
        return start, end

    if current_duration < target_duration:
        needed = target_duration - current_duration
        extend_left = min(start, needed / 2.0)
        extend_right = min(total_duration - end, needed - extend_left)
        start -= extend_left
        end += extend_right

        remaining = target_duration - (end - start)
        if remaining > 0:
            extra_left = min(start, remaining)
            start -= extra_left
            remaining -= extra_left
        if remaining > 0:
            extra_right = min(total_duration - end, remaining)
            end += extra_right

    return max(0.0, start), min(total_duration, end)


def set_ratio_preset(preset):
    global OUTPUT_RATIO, OUT_WIDTH, OUT_HEIGHT
    OUTPUT_RATIO = preset
    if preset == "9:16":
        if LIGHTWEIGHT_EXPORT:
            OUT_WIDTH, OUT_HEIGHT = LIGHTWEIGHT_WIDTH, LIGHTWEIGHT_HEIGHT
        else:
            OUT_WIDTH, OUT_HEIGHT = 1080, 1920
        return
    if preset == "1:1":
        OUT_WIDTH, OUT_HEIGHT = 720, 720
        return
    if preset == "16:9":
        OUT_WIDTH, OUT_HEIGHT = 1280, 720
        return
    if preset == "original":
        OUT_WIDTH, OUT_HEIGHT = None, None
        return
    raise ValueError("Invalid ratio preset")

def ffmpeg_tersedia():
    return bool(shutil.which("ffmpeg"))


def coba_masukkan_ffmpeg_ke_path():
    if ffmpeg_tersedia():
        return True

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return False

    winget_packages = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
    gyan_root = os.path.join(winget_packages, "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe")
    if not os.path.isdir(gyan_root):
        return False

    found_bin_dir = None
    for root, dirs, files in os.walk(gyan_root):
        if "ffmpeg.exe" in files and os.path.basename(root).lower() == "bin":
            found_bin_dir = root
            break

    if not found_bin_dir:
        return False

    os.environ["PATH"] = f"{found_bin_dir};{os.environ.get('PATH', '')}"
    return ffmpeg_tersedia()


def parse_args():
    parser = argparse.ArgumentParser(prog="yt-heatmap-clipper")
    parser.add_argument("--url", help="YouTube URL (watch/shorts/youtu.be)")
    parser.add_argument(
        "--crop",
        choices=["default", "split_left", "split_right"],
        help="Crop mode",
    )
    parser.add_argument(
        "--subtitle",
        choices=["y", "n"],
        help="Enable auto subtitle (y/n)",
    )
    parser.add_argument("--whisper-model", dest="whisper_model", help="Faster-Whisper model")
    parser.add_argument("--whisper-language", dest="whisper_language", help="Whisper language code (e.g., id, en). Default: auto-detect")
    parser.add_argument("--subtitle-font", dest="subtitle_font", help="Subtitle font name (e.g., Poppins)")
    parser.add_argument("--subtitle-fontsdir", dest="subtitle_fontsdir", help="Folder containing .ttf/.otf fonts")
    parser.add_argument(
        "--subtitle-location",
        dest="subtitle_location",
        choices=["center", "bottom"],
        help="Subtitle placement: center or bottom",
    )
    parser.add_argument("--subtitle-outline", dest="subtitle_outline", type=int, help="Subtitle outline thickness in pixels (0=no outline, default=2)")
    parser.add_argument("--subtitle-shadow", dest="subtitle_shadow", type=int, help="Subtitle shadow depth in pixels (0=no shadow, default=1)")
    parser.add_argument("--ratio", choices=["9:16", "1:1", "16:9", "original"], help="Output ratio preset")
    parser.add_argument("--check", action="store_true", help="Check dependencies then exit")
    parser.add_argument("--no-update-ytdlp", action="store_true", help="Skip auto-update yt-dlp")
    parser.add_argument("--cookies", dest="cookies", help="Path to YouTube cookies file (Netscape format)")
    return parser.parse_args()


def escape_subtitles_filter_path(path):
    abs_path = os.path.abspath(path)
    return abs_path.replace("\\", "/").replace(":", "\\:")


def escape_subtitles_filter_dir(path):
    abs_path = os.path.abspath(path)
    return abs_path.replace("\\", "/").replace(":", "\\:")

def build_subtitle_force_style():
    alignment = "2" if SUBTITLE_LOCATION == "bottom" else "5"
    margin_v = "40" if SUBTITLE_LOCATION == "bottom" else "0"
    border_style = "3" if SUBTITLE_OUTLINE == 0 and SUBTITLE_SHADOW == 0 else "1"
    return (
        f"FontName={SUBTITLE_FONT},FontSize=12,Bold=1,"
        f"PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
        f"BorderStyle={border_style},Outline={SUBTITLE_OUTLINE},Shadow={SUBTITLE_SHADOW},"
        f"Alignment={alignment},MarginV={margin_v}"
    )


def build_cover_scale_crop_vf(out_w, out_h):
    ar_expr = f"{out_w}/{out_h}"
    scale = f"scale='if(gte(iw/ih,{ar_expr}),-2,{out_w})':'if(gte(iw/ih,{ar_expr}),{out_h},-2)'"
    crop = f"crop={out_w}:{out_h}:(iw-{out_w})/2:(ih-{out_h})/2"
    return f"{scale},{crop}"


def build_cover_scale_vf(out_w, out_h):
    ar_expr = f"{out_w}/{out_h}"
    scale = f"scale='if(gte(iw/ih,{ar_expr}),-2,{out_w})':'if(gte(iw/ih,{ar_expr}),{out_h},-2)'"
    return scale


def get_split_heights(out_h):
    if not out_h:
        return None, None
    bottom = min(BOTTOM_HEIGHT, max(1, out_h - 1))
    top = max(1, out_h - bottom)
    return top, bottom
def extract_video_id(url):
    """
    Extract the YouTube video ID from a given URL.
    Supports standard YouTube URLs, shortened URLs, and Shorts URLs.
    """
    parsed = urlparse(url)

    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return parsed.path[1:]

    if parsed.hostname in ("youtube.com", "www.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]

    return None


def get_model_size(model):
    """
    Get the approximate size of a Whisper model.
    """
    sizes = {
        "tiny": "75 MB",
        "base": "142 MB",
        "small": "466 MB",
        "medium": "1.5 GB",
        "large-v1": "2.9 GB",
        "large-v2": "2.9 GB",
        "large-v3": "2.9 GB"
    }
    return sizes.get(model, "unknown size")


def cek_dependensi(install_whisper=False, fatal=True):
    """
    Ensure required dependencies are available.
    Automatically updates yt-dlp and checks FFmpeg availability.
    """
    global WHISPER_MODEL
    args = getattr(cek_dependensi, "_args", None)
    skip_update = bool(getattr(args, "no_update_ytdlp", False)) if args else False

    if not skip_update:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    if not shutil.which("deno"):
        print("⚠️  deno tidak ditemukan. yt-dlp butuh JS runtime untuk YouTube.")
        print("   Install: curl -fsSL https://deno.land/install.sh | sh")
        print("   Atau: brew install deno (macOS)")
        print()

    if install_whisper:
        # Check if faster-whisper package is installed
        try:
            import faster_whisper
            print(f"✅ Faster-Whisper package installed.")
            
            # Check if selected model is cached
            cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
            model_name = f"faster-whisper-{WHISPER_MODEL}"
            
            model_cached = False
            if os.path.exists(cache_dir):
                try:
                    cached_items = os.listdir(cache_dir)
                    model_cached = any(model_name in item.lower() for item in cached_items)
                except Exception:
                    pass
            
            if model_cached:
                print(f"✅ Model '{WHISPER_MODEL}' already cached and ready.\n")
            else:
                print(f"⚠️  Model '{WHISPER_MODEL}' not found in cache.")
                print(f"   📥 Will auto-download ~{get_model_size(WHISPER_MODEL)} on first transcribe.")
                print(f"   ⏱️  Download happens only once, then cached for future use.\n")
                
        except ImportError:
            print("📦 Installing Faster-Whisper package...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "faster-whisper"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✅ Faster-Whisper package installed successfully.")
            print(f"⚠️  Model '{WHISPER_MODEL}' (~{get_model_size(WHISPER_MODEL)}) will be downloaded on first use.\n")

    coba_masukkan_ffmpeg_ke_path()
    if not ffmpeg_tersedia():
        print("FFmpeg not found. Please install FFmpeg and ensure it is in PATH.")
        if fatal:
            sys.exit(1)
        return False
    return True


def build_ytdlp_base_cmd():
    """Build yt-dlp base command with cookies if available."""
    cmd = [sys.executable, "-m", "yt_dlp"]
    if YTDLP_COOKIES and os.path.isfile(YTDLP_COOKIES):
        cmd.extend(["--cookies", YTDLP_COOKIES])
    return cmd


def get_available_encoders():
    global _AVAILABLE_ENCODERS
    if _AVAILABLE_ENCODERS is not None:
        return _AVAILABLE_ENCODERS

    try:
        res = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=True,
        )
        encoders = set()
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0][0] in {"V", "A", "S"}:
                encoders.add(parts[1])
        _AVAILABLE_ENCODERS = encoders
    except Exception:
        _AVAILABLE_ENCODERS = set()

    return _AVAILABLE_ENCODERS


def get_media_duration_seconds(file_path):
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float((res.stdout or "").strip())
    except Exception:
        return None


def probe_media_streams(file_path):
    try:
        res = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=index,codec_type,start_time,duration",
                "-of", "json",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout or "{}")
        return data.get("streams") or []
    except Exception:
        return []


def segment_has_audio_offset_issue(file_path):
    streams = probe_media_streams(file_path)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)

    if audio_stream is None:
        return True, "missing audio stream"

    try:
        audio_start = float(audio_stream.get("start_time", 0.0) or 0.0)
    except Exception:
        audio_start = 0.0

    try:
        video_start = float(video_stream.get("start_time", 0.0) or 0.0) if video_stream else 0.0
    except Exception:
        video_start = 0.0

    if audio_start > AUDIO_START_TOLERANCE:
        return True, f"audio starts late at {audio_start:.3f}s"

    if abs(audio_start - video_start) > AUDIO_START_TOLERANCE:
        return True, f"audio/video start drift {abs(audio_start - video_start):.3f}s"

    return False, ""


def is_duration_close_enough(actual_duration, expected_duration):
    if actual_duration is None:
        return False
    expected_duration = max(0.0, float(expected_duration))
    if expected_duration <= 0:
        return False
    min_acceptable = min(
        max(0.0, expected_duration - SEGMENT_DURATION_TOLERANCE),
        expected_duration * 0.9,
    )
    return float(actual_duration) >= min_acceptable


def build_video_codec_args():
    encoders = get_available_encoders()
    if "libx264" in encoders:
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
    if "libopenh264" in encoders:
        return ["-c:v", "libopenh264", "-b:v", "5000k"]
    raise RuntimeError("No supported H.264 encoder found. Install FFmpeg with libx264 or libopenh264 support.")


def build_normalized_audio_args(audio_duration=None):
    audio_filter = "aresample=async=1:first_pts=0"
    if audio_duration is not None:
        duration = max(0.0, float(audio_duration))
        audio_filter = (
            f"atrim=start=0:duration={duration},"
            "asetpts=N/SR/TB,"
            "aresample=async=1:first_pts=0"
        )
    return [
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-ac", "2",
        "-af", audio_filter,
    ]


def build_download_commands(video_id, output_file, start=None, duration=None):
    # Allow VP9/AV1 sources for highest quality; ffmpeg will transcode during crop anyway.
    format_selector = (
        "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/"
        "bv*[height<=1080]+ba/"
        "b[height<=1080]/"
        "bv*+ba/b"
    )
    fallback_selector = "bv*+ba/b"

    def make_command(selector):
        cmd = [
            *build_ytdlp_base_cmd(),
            "--force-ipv4",
            "--force-overwrites",
            "--quiet", "--no-warnings",
            "--merge-output-format", "mkv",
            "-f", selector,
            "-o", output_file,
            f"https://youtu.be/{video_id}",
        ]
        if start is not None and duration is not None:
            cmd[5:5] = [
                "--downloader", "ffmpeg",
                "--downloader-args",
                (
                    f"ffmpeg_i:-ss {start} -t {duration} "
                    "-hide_banner -loglevel error"
                ),
            ]
        return cmd

    return make_command(format_selector), make_command(fallback_selector)


def run_download_command(cmd_primary, cmd_fallback):
    try:
        subprocess.run(
            cmd_primary,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if "Requested format is not available" not in stderr:
            raise
        subprocess.run(
            cmd_fallback,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


def cleanup_temp_files(index, extra_paths=None):
    paths = set(extra_paths or [])
    for prefix in (f"temp_segment_{index}", f"temp_full_{index}"):
        paths.update(glob.glob(f"{prefix}*"))

    for path in paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


def build_export_audio_args(audio_duration=None):
    return [
        "-map", "0:v:0",
        "-map", "0:a:0?",
        *build_normalized_audio_args(audio_duration),
        "-shortest",
    ]


def normalize_output_for_publish(output_file, max_duration=None, event_hook=None, log_hook=None):
    normalized_file = output_file + ".normalized.mp4"
    trim_args = []
    if max_duration is not None:
        trim_args = ["-t", str(max(0.0, float(max_duration)))]
    cmd_normalize = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", output_file,
        *trim_args,
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", "setsar=1,format=yuv420p",
        *build_video_codec_args(),
        *build_normalized_audio_args(max_duration),
        "-movflags", "+faststart",
        "-shortest",
        normalized_file,
    ]

    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "normalize"})
        except Exception:
            pass

    emit_log("  Normalizing clip for publish compatibility...", log_hook=log_hook)
    subprocess.run(
        cmd_normalize,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    os.replace(normalized_file, output_file)


def assert_valid_output_file(output_file):
    if not os.path.exists(output_file):
        raise RuntimeError("Output clip tidak dibuat oleh FFmpeg.")
    file_size = os.path.getsize(output_file)
    if file_size < 1024 * 1024:
        raise RuntimeError(f"Output clip invalid atau terlalu kecil ({file_size} bytes).")
    streams = probe_media_streams(output_file)
    has_video = any(s.get("codec_type") == "video" for s in streams)
    if not has_video:
        raise RuntimeError("Output clip invalid: tidak ada video stream.")
    duration = get_media_duration_seconds(output_file)
    if duration is None or duration <= 0:
        raise RuntimeError("Output clip invalid: durasi tidak terbaca.")


def ambil_most_replayed(video_id):
    """
    Fetch and parse YouTube 'Most Replayed' heatmap data.
    Returns a list of high-engagement segments.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}

    print("Reading YouTube heatmap data...")

    cookies_dict = {}
    if YTDLP_COOKIES and os.path.isfile(YTDLP_COOKIES):
        try:
            with open(YTDLP_COOKIES, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 7:
                        cookies_dict[parts[5]] = parts[6]
        except Exception:
            pass

    try:
        html = requests.get(url, headers=headers, cookies=cookies_dict, timeout=20).text
    except Exception:
        return []

    match = re.search(
        r'"markers":\s*(\[.*?\])\s*,\s*"?markersMetadata"?',
        html,
        re.DOTALL
    )

    if not match:
        return []

    try:
        markers = json.loads(match.group(1).replace('\\"', '"'))
    except Exception:
        return []

    results = []

    for marker in markers:
        if "heatMarkerRenderer" in marker:
            marker = marker["heatMarkerRenderer"]

        try:
            score = float(marker.get("intensityScoreNormalized", 0))
            if score >= MIN_SCORE:
                results.append({
                    "start": float(marker["startMillis"]) / 1000,
                    "duration": min(
                        float(marker["durationMillis"]) / 1000,
                        MAX_DURATION
                    ),
                    "score": score
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_duration(video_id):
    """
    Retrieve the total duration of a YouTube video in seconds.
    """
    cmd = [
        *build_ytdlp_base_cmd(),
        "--get-duration",
        f"https://youtu.be/{video_id}"
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        time_parts = res.stdout.strip().split(":")

        if len(time_parts) == 2:
            return int(time_parts[0]) * 60 + int(time_parts[1])
        if len(time_parts) == 3:
            return (
                int(time_parts[0]) * 3600 +
                int(time_parts[1]) * 60 +
                int(time_parts[2])
            )
    except Exception:
        pass

    return 3600


def generate_subtitle(video_file, subtitle_file, event_hook=None, log_hook=None):
    """
    Generate subtitle file using Faster-Whisper for the given video.
    Returns True if successful, False otherwise.
    """
    from faster_whisper import WhisperModel

    def load_and_transcribe():
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle_model_load"})
            except Exception:
                pass
        emit_log(f"  Loading Faster-Whisper model '{WHISPER_MODEL}'...", log_hook=log_hook)
        emit_log(f"  (If this is first time, downloading ~{get_model_size(WHISPER_MODEL)}...)", log_hook=log_hook)
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        emit_log("  Model loaded. Transcribing audio...", log_hook=log_hook)
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "subtitle_transcribe"})
            except Exception:
                pass
        segments, info = model.transcribe(video_file, language=WHISPER_LANGUAGE)
        return segments

    try:
        segments = load_and_transcribe()
    except Exception as e:
        msg = str(e)
        if os.name == "nt" and "WinError 1314" in msg:
            emit_log(f"  Failed to generate subtitle: {msg}", log_hook=log_hook)
            emit_log("  Windows symlink cache permission issue detected.", log_hook=log_hook)
            emit_log("  Retrying subtitle generation once...", log_hook=log_hook)
            try:
                segments = load_and_transcribe()
            except Exception as e2:
                emit_log(f"  Failed to generate subtitle: {str(e2)}", log_hook=log_hook)
                return False
        else:
            emit_log(f"  Failed to generate subtitle: {msg}", log_hook=log_hook)
            return False

    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "subtitle_write"})
        except Exception:
            pass
    emit_log("  Generating subtitle file...", log_hook=log_hook)
    with open(subtitle_file, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)
            text = segment.text.strip()

            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")

    return True


def format_timestamp(seconds):
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def proses_satu_clip(video_id, item, index, total_duration, crop_mode="default", use_subtitle=False, event_hook=None, log_hook=None):
    """
    Download, crop, and export a single vertical clip
    based on a heatmap segment.
    
    Args:
        crop_mode: "default", "split_left", or "split_right"
        use_subtitle: whether to generate and burn subtitle
    """
    start_original = item["start"]
    source_duration = item["duration"]
    end_original = item["start"] + item["duration"]

    start, end = resolve_clip_window(
        start_original=start_original,
        source_duration=source_duration,
        total_duration=total_duration,
    )

    if end - start < 3:
        return False

    segment_file = f"temp_segment_{index}.mkv"
    full_file = f"temp_full_{index}.mkv"
    cropped_file = f"temp_cropped_{index}.mp4"
    subtitle_file = f"temp_{index}.srt"
    output_file = os.path.join(OUTPUT_DIR, f"clip_{index}.mp4")

    # Clean leftover temp files from previous failed runs
    cleanup_temp_files(index, [segment_file, full_file, cropped_file, subtitle_file])

    video_codec_args = build_video_codec_args()
    expected_duration = max(0.0, end - start)
    source_file = segment_file
    source_seek_args = []

    emit_log(
        f"[Clip {index}] Processing segment "
        f"({int(start)}s - {int(end)}s, final {int(end - start)}s, "
        f"marker {int(source_duration)}s, padding target {PADDING}s)",
        log_hook=log_hook
    )
    if callable(event_hook):
        try:
            event_hook("stage", {"stage": "download", "clip_index": index})
        except Exception:
            pass

    cmd_download, cmd_download_fallback = build_download_commands(
        video_id=video_id,
        output_file=segment_file,
        start=start,
        duration=expected_duration,
    )
    cmd_download_full, cmd_download_full_fallback = build_download_commands(
        video_id=video_id,
        output_file=full_file,
    )

    try:
        if ALWAYS_FULL_DOWNLOAD_TRIM:
            emit_log(
                "  Using full download + local trim for safer audio sync and exact duration...",
                log_hook=log_hook,
            )
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "download_fallback", "clip_index": index})
                except Exception:
                    pass
            run_download_command(cmd_download_full, cmd_download_full_fallback)
            if not os.path.exists(full_file):
                emit_log("Failed to download fallback source video.", log_hook=log_hook)
                return False
            source_file = full_file
            source_seek_args = ["-ss", str(start), "-t", str(expected_duration)]
        else:
            run_download_command(cmd_download, cmd_download_fallback)

            if not os.path.exists(segment_file):
                emit_log("Failed to download video segment.", log_hook=log_hook)
                return False

            segment_duration = get_media_duration_seconds(segment_file)
            offset_issue, offset_reason = segment_has_audio_offset_issue(segment_file)
            too_long = segment_duration is not None and segment_duration > expected_duration + SEGMENT_DURATION_TOLERANCE
            if not is_duration_close_enough(segment_duration, expected_duration) or offset_issue or too_long:
                if os.path.exists(segment_file):
                    try:
                        os.remove(segment_file)
                    except Exception:
                        pass

                if too_long:
                    fallback_reason = f"segment duration {segment_duration:.2f}s above target"
                else:
                    fallback_reason = (
                        (
                            f"segment duration {segment_duration:.2f}s below target"
                            if segment_duration is not None
                            else "segment duration probe failed"
                        )
                        if not is_duration_close_enough(segment_duration, expected_duration)
                        else offset_reason
                    )
                emit_log(
                    "  Segment download is not safe for export "
                    f"({fallback_reason}); falling back to full download + local trim...",
                    log_hook=log_hook,
                )
                if callable(event_hook):
                    try:
                        event_hook("stage", {"stage": "download_fallback", "clip_index": index})
                    except Exception:
                        pass

                run_download_command(cmd_download_full, cmd_download_full_fallback)
                if not os.path.exists(full_file):
                    emit_log("Failed to download fallback source video.", log_hook=log_hook)
                    return False

                source_file = full_file
                source_seek_args = ["-ss", str(start), "-t", str(expected_duration)]
            else:
                source_seek_args = ["-t", str(expected_duration)]
                emit_log(
                    f"  Downloaded source segment duration: {segment_duration:.2f}s",
                    log_hook=log_hook,
                )

        out_w, out_h = OUT_WIDTH, OUT_HEIGHT
        normalize_vf_suffix = ",setsar=1,format=yuv420p"
        if crop_mode == "default":
            if OUTPUT_RATIO == "original":
                vf = "setsar=1,format=yuv420p"
                cmd_crop = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", source_file, *source_seek_args,
                    "-vf", vf,
                    *video_codec_args,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    cropped_file
                ]
            else:
                vf = build_cover_scale_crop_vf(out_w, out_h) + normalize_vf_suffix
                cmd_crop = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", source_file, *source_seek_args,
                    "-vf", vf,
                    *video_codec_args,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    cropped_file
                ]
        elif crop_mode == "split_left":
            if OUTPUT_RATIO == "original" or not out_w or not out_h or out_h < out_w:
                vf = build_cover_scale_crop_vf(out_w or 720, out_h or 1280) + normalize_vf_suffix if OUTPUT_RATIO != "original" else "setsar=1,format=yuv420p"
                cmd_crop = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", source_file, *source_seek_args,
                    "-vf", vf,
                    *video_codec_args,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    cropped_file
                ]
            else:
                top_h, bottom_h = get_split_heights(out_h)
                scaled = build_cover_scale_vf(out_w, out_h)
                vf = (
                    f"{scaled}[scaled];"
                    f"[scaled]split=2[s1][s2];"
                    f"[s1]crop={out_w}:{top_h}:(iw-{out_w})/2:(ih-{out_h})/2[top];"
                    f"[s2]crop={out_w}:{bottom_h}:0:ih-{bottom_h}[bottom];"
                    f"[top][bottom]vstack,setsar=1,format=yuv420p[out]"
                )
                cmd_crop = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", source_file, *source_seek_args,
                    "-filter_complex", vf,
                    "-map", "[out]", "-map", "0:a:0?",
                    *video_codec_args,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-shortest",
                    cropped_file
                ]
        elif crop_mode == "split_right":
            if OUTPUT_RATIO == "original" or not out_w or not out_h or out_h < out_w:
                vf = build_cover_scale_crop_vf(out_w or 720, out_h or 1280) + normalize_vf_suffix if OUTPUT_RATIO != "original" else "setsar=1,format=yuv420p"
                cmd_crop = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", source_file, *source_seek_args,
                    "-vf", vf,
                    *video_codec_args,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    cropped_file
                ]
            else:
                top_h, bottom_h = get_split_heights(out_h)
                scaled = build_cover_scale_vf(out_w, out_h)
                vf = (
                    f"{scaled}[scaled];"
                    f"[scaled]split=2[s1][s2];"
                    f"[s1]crop={out_w}:{top_h}:(iw-{out_w})/2:(ih-{out_h})/2[top];"
                    f"[s2]crop={out_w}:{bottom_h}:iw-{out_w}:ih-{bottom_h}[bottom];"
                    f"[top][bottom]vstack,setsar=1,format=yuv420p[out]"
                )
                cmd_crop = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", source_file, *source_seek_args,
                    "-filter_complex", vf,
                    "-map", "[out]", "-map", "0:a:0?",
                    *video_codec_args,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-shortest",
                    cropped_file
                ]

        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "crop", "clip_index": index})
            except Exception:
                pass
        emit_log("  Cropping video...", log_hook=log_hook)
        subprocess.run(
            cmd_crop,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        cleanup_temp_files(index, [segment_file, full_file])

        # Generate and burn subtitle if enabled
        if use_subtitle:
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "subtitle", "clip_index": index})
                except Exception:
                    pass
            emit_log("  Generating subtitle...", log_hook=log_hook)
            if generate_subtitle(cropped_file, subtitle_file, event_hook=event_hook, log_hook=log_hook):
                if callable(event_hook):
                    try:
                        event_hook("stage", {"stage": "burn_subtitle", "clip_index": index})
                    except Exception:
                        pass
                emit_log("  Burning subtitle to video...", log_hook=log_hook)
                # Get absolute path for subtitle file
                subtitle_path = escape_subtitles_filter_path(subtitle_file)
                fonts_dir = SUBTITLE_FONTS_DIR
                fontsdir_arg = ""
                if fonts_dir and os.path.isdir(fonts_dir):
                    fontsdir_arg = f":fontsdir='{escape_subtitles_filter_dir(fonts_dir)}'"
                
                force_style = build_subtitle_force_style()
                cmd_subtitle = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", cropped_file,
                    "-t", str(expected_duration),
                    "-vf", f"subtitles='{subtitle_path}'{fontsdir_arg}:force_style='{force_style}',setsar=1,format=yuv420p",
                    *video_codec_args,
                    "-c:a", "copy",
                    "-movflags", "+faststart",
                    output_file
                ]
                
                subprocess.run(
                    cmd_subtitle,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                os.remove(cropped_file)
                os.remove(subtitle_file)
            else:
                # If subtitle generation failed, use cropped file as output
                emit_log("  Subtitle generation failed, continuing without subtitle...", log_hook=log_hook)
                if callable(event_hook):
                    try:
                        event_hook("stage", {"stage": "finalize", "clip_index": index})
                    except Exception:
                        pass
                os.rename(cropped_file, output_file)
        else:
            # No subtitle, rename cropped file to output
            if callable(event_hook):
                try:
                    event_hook("stage", {"stage": "finalize", "clip_index": index})
                except Exception:
                    pass
            os.rename(cropped_file, output_file)

        assert_valid_output_file(output_file)

        emit_log("Clip successfully generated.", log_hook=log_hook)
        if callable(event_hook):
            try:
                event_hook("stage", {"stage": "done_clip", "clip_index": index})
            except Exception:
                pass
        return True

    except subprocess.CalledProcessError as e:
        cleanup_temp_files(
            index,
            [segment_file, full_file, cropped_file, subtitle_file],
        )

        emit_log("Failed to generate this clip.", log_hook=log_hook)
        detail = (e.stderr or e.stdout or "").strip()
        if detail:
            emit_log(f"Error details: {detail}", log_hook=log_hook)
        return False
    except Exception as e:
        cleanup_temp_files(
            index,
            [segment_file, full_file, cropped_file, subtitle_file],
        )

        emit_log("Failed to generate this clip.", log_hook=log_hook)
        emit_log(f"Error: {str(e)}", log_hook=log_hook)
        return False


def main():
    """
    Main entry point of the application.
    """
    args = parse_args()
    cek_dependensi._args = args

    if args.whisper_model:
        global WHISPER_MODEL
        WHISPER_MODEL = args.whisper_model
    if args.whisper_language:
        global WHISPER_LANGUAGE
        WHISPER_LANGUAGE = args.whisper_language
    if args.subtitle_font:
        global SUBTITLE_FONT
        SUBTITLE_FONT = args.subtitle_font
    if args.subtitle_fontsdir:
        global SUBTITLE_FONTS_DIR
        SUBTITLE_FONTS_DIR = args.subtitle_fontsdir
    if args.subtitle_location:
        global SUBTITLE_LOCATION
        SUBTITLE_LOCATION = args.subtitle_location
    if args.subtitle_outline is not None:
        global SUBTITLE_OUTLINE
        SUBTITLE_OUTLINE = max(0, args.subtitle_outline)
    if args.subtitle_shadow is not None:
        global SUBTITLE_SHADOW
        SUBTITLE_SHADOW = max(0, args.subtitle_shadow)
    if args.cookies:
        global YTDLP_COOKIES
        YTDLP_COOKIES = args.cookies
    if args.ratio:
        set_ratio_preset(args.ratio)

    if args.check:
        cek_dependensi(install_whisper=False)
        print("✅ Basic dependencies OK.")
        return

    coba_masukkan_ffmpeg_ke_path()
    if not ffmpeg_tersedia():
        print("FFmpeg not found. Please install FFmpeg and ensure it is in PATH.")
        return

    crop_mode = args.crop
    crop_desc = None
    if crop_mode:
        crop_desc = {
            "default": "Default center crop",
            "split_left": "Split crop (bottom-left facecam)",
            "split_right": "Split crop (bottom-right facecam)",
        }[crop_mode]

    subtitle_choice = args.subtitle
    if subtitle_choice:
        use_subtitle = subtitle_choice == "y"
    else:
        use_subtitle = None

    link = args.url

    if crop_mode is None or use_subtitle is None or not link:
        print("\n=== Crop Mode ===")
        print("1. Default (center crop)")
        print("2. Split 1 (top: center, bottom: bottom-left (facecam))")
        print("3. Split 2 (top: center, bottom: bottom-right ((facecam))")

        while crop_mode is None:
            choice = input("\nSelect crop mode (1-3): ").strip()
            if choice == "1":
                crop_mode = "default"
                crop_desc = "Default center crop"
                break
            if choice == "2":
                crop_mode = "split_left"
                crop_desc = "Split crop (bottom-left facecam)"
                break
            if choice == "3":
                crop_mode = "split_right"
                crop_desc = "Split crop (bottom-right facecam)"
                break
            print("Invalid choice. Please enter 1, 2, or 3.")

        print(f"Selected: {crop_desc}")

        print("\n=== Auto Subtitle ===")
        print(f"Available model: {WHISPER_MODEL} (~{get_model_size(WHISPER_MODEL)})")
        while use_subtitle is None:
            subtitle_choice = input("Add auto subtitle using Faster-Whisper? (y/n): ").strip().lower()
            if subtitle_choice in ["y", "yes"]:
                use_subtitle = True
            elif subtitle_choice in ["n", "no"]:
                use_subtitle = False
            else:
                print("Invalid choice. Please enter y or n.")

        if use_subtitle:
            print(f"✅ Subtitle enabled (Model: {WHISPER_MODEL}, Bahasa Indonesia)")
        else:
            print("❌ Subtitle disabled")

        print()

        cek_dependensi(install_whisper=use_subtitle)

        if not link:
            link = input("Link YT: ").strip()
    else:
        cek_dependensi(install_whisper=use_subtitle)

    video_id = extract_video_id(link)

    if not video_id:
        print("Invalid YouTube link.")
        return

    heatmap_data = ambil_most_replayed(video_id)

    if not heatmap_data:
        print("No high-engagement segments found.")
        return

    print(f"Found {len(heatmap_data)} high-engagement segments.")

    total_duration = get_duration(video_id)
    global OUTPUT_DIR
    if OUTPUT_DIR == DEFAULT_READY_DIR:
        OUTPUT_DIR = os.path.join(DEFAULT_READY_DIR, manifest_helper.build_job_id())
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(
        f"Processing clips with {PADDING}s pre-padding "
        f"and {PADDING}s post-padding."
    )
    print(f"Using crop mode: {crop_desc}")

    success_count = 0

    for item in heatmap_data:
        if success_count >= MAX_CLIPS:
            break

        if proses_satu_clip(
            video_id,
            item,
            success_count + 1,
            total_duration,
            crop_mode,
            use_subtitle
        ):
            success_count += 1

    print(
        f"Finished processing. "
        f"{success_count} clip(s) successfully saved to '{OUTPUT_DIR}'."
    )

    if success_count > 0:
        source_meta = manifest_helper.fetch_source_metadata(link)
        manifest = manifest_helper.write_job_manifest(
            OUTPUT_DIR,
            link,
            video_id,
            subtitle_enabled=use_subtitle,
            crop_mode=crop_mode,
            ratio=OUTPUT_RATIO,
            padding=PADDING,
            **source_meta,
        )
        print(f"Manifest saved to '{manifest['manifest_path']}'.")


if __name__ == "__main__":
    main()
