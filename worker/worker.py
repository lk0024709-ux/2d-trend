#!/usr/bin/env python3
"""Deterministic 2D Trend render worker. Requires FFmpeg, FFprobe and Pillow."""
from __future__ import annotations
import argparse
import ipaddress
import json
import math
import re
import socket
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS = 90
W, H, FPS = 720, 1280, 24

def run(cmd: list[str], capture: bool = False) -> str:
    result = subprocess.run(cmd, check=True, text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE)
    return result.stdout if capture else ""

def probe(path: Path) -> dict:
    data = json.loads(run(["ffprobe", "-v", "error", "-show_streams",
        "-show_format", "-of", "json", str(path)], True))
    streams = data.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("Input has no video stream")
    duration = float(data.get("format", {}).get("duration", 0))
    width, height = int(video["width"]), int(video["height"])
    if duration <= 0 or duration > MAX_SECONDS:
        raise ValueError(f"Video duration must be between 0 and {MAX_SECONDS} seconds")
    if width < 320 or height < 320 or width > 3840 or height > 2160:
        raise ValueError("Video resolution must be between 320px and 3840x2160")
    return {"duration": duration, "width": width, "height": height,
            "has_audio": any(item.get("codec_type") == "audio" for item in streams)}

def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS media URLs are allowed")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("Local network media URLs are blocked")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
        except OSError as exc:
            raise ValueError("Media host could not be resolved") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Private or reserved network media URLs are blocked")

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def download(url: str, target: Path) -> None:
    validate_public_url(url)
    opener = urllib.request.build_opener(SafeRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "2DTrendStudio/0.1"})
    total = 0
    with opener.open(request, timeout=30) as response, target.open("wb") as output:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_BYTES:
            raise ValueError("Media exceeds 100 MB")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("Media exceeds 100 MB")
            output.write(chunk)

def font(size: int):
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()

def wrap(draw, text: str, selected_font, max_width: int):
    words, lines, line = text.split(), [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=selected_font)[2] > max_width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines

ALLOWED_STATES = {
    "queued": {"validating", "cancelled", "failed"},
    "validating": {"scripting", "generating_assets", "failed", "cancelled"},
    "scripting": {"awaiting_approval", "failed", "cancelled"},
    "awaiting_approval": {"generating_assets", "cancelled", "failed"},
    "generating_assets": {"rendering", "failed", "cancelled"},
    "rendering": {"quality_check", "failed", "cancelled"},
    "quality_check": {"completed", "failed"},
    "completed": set(), "failed": set(), "cancelled": set()
}

def validate_manifest(manifest: dict) -> None:
    if manifest.get("version") != 1:
        raise ValueError("Unsupported manifest version")
    if manifest.get("mode") not in ("topic", "video"):
        raise ValueError("mode must be topic or video")
    output = manifest.get("output", {})
    if output and (output.get("width", 1080) != 1080 or output.get("height", 1920) != 1920):
        raise ValueError("MVP output must be 1080x1920")
    if manifest["mode"] == "topic":
        topic = str(manifest.get("topic", "")).strip()
        if not 4 <= len(topic) <= 500:
            raise ValueError("Topic must contain 4-500 characters")
        if not 5 <= int(manifest.get("duration_seconds", 15)) <= 60:
            raise ValueError("Topic duration must be 5-60 seconds")
        if len(str(manifest.get("script", ""))) > 5000:
            raise ValueError("Script must be 5000 characters or fewer")
    else:
        media_path = str(manifest.get("media_path", "")).strip()
        media_url = str(manifest.get("media_url", ""))
        if not media_path and not media_url.startswith("https://"):
            raise ValueError("Video mode requires an HTTPS media_url")

def transition_job(current: str, next_state: str) -> str:
    if next_state not in ALLOWED_STATES.get(current, set()):
        raise ValueError(f"Invalid job transition: {current} -> {next_state}")
    return next_state

def validate_timeline(shots: list[dict], duration: float) -> bool:
    if not shots or abs(float(shots[0]["start"])) > 0.01:
        return False
    cursor = 0.0
    for shot in shots:
        start, end = float(shot["start"]), float(shot["end"])
        if abs(start - cursor) > 0.02 or end <= start:
            return False
        cursor = end
    return abs(cursor - duration) <= 0.05

def make_topic_frames(manifest: dict, outdir: Path) -> tuple[float, list[dict]]:
    duration = max(5, min(int(manifest.get("duration_seconds", 15)), 60))
    total = duration * FPS
    topic = str(manifest["topic"])
    script = str(manifest.get("script") or topic)
    chunks = [part.strip() for part in re.split(r"(?<=[.!?।])\s+|\n+", script) if part.strip()] or [topic]
    captions = []
    scene_len = duration / len(chunks)
    for index, chunk in enumerate(chunks):
        captions.append({"text": chunk, "start": round(index * scene_len, 3),
                         "end": round((index + 1) * scene_len, 3), "timing": "phrase-level"})
    palette = [(25, 34, 57), (50, 30, 65), (25, 58, 61), (63, 40, 35)]
    for frame in range(total):
        timestamp = frame / FPS
        index = min(len(chunks) - 1, int(timestamp / scene_len))
        local = (timestamp - index * scene_len) / scene_len
        image = Image.new("RGB", (W, H), palette[index % len(palette)])
        draw = ImageDraw.Draw(image)
        cx = int(W * (0.72 - 0.12 * local))
        cy = int(H * (0.22 + 0.05 * math.sin(timestamp * 2)))
        for radius in (90, 145, 205):
            draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                         outline=(105, 139, 94), width=3)
        draw.rounded_rectangle((52, 90, 68, 250), radius=8, fill=(201, 255, 88))
        draw.text((52, 300), "2D TREND / STORY", font=font(22), fill=(201, 255, 88))
        selected_font = font(54)
        lines = wrap(draw, chunks[index], selected_font, W - 110)
        y = 470 - int(18 * math.sin(local * math.pi))
        for line in lines[:5]:
            draw.text((52, y), line, font=selected_font, fill=(255, 255, 255),
                      stroke_width=2, stroke_fill=(15, 15, 22))
            y += 72
        draw.text((52, 1130), f"{manifest.get('language', 'English').upper()}  •  {index+1:02d}/{len(chunks):02d}",
                  font=font(18), fill=(205, 205, 215))
        image.save(outdir / f"frame_{frame:05d}.png", optimize=True)
    return float(duration), captions

def detect_shots(video: Path, duration: float) -> list[dict]:
    command = ["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
               "select='gt(scene,0.30)',showinfo", "-an", "-f", "null", "-"]
    result = subprocess.run(command, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    points = []
    for match in re.finditer(r"pts_time:([0-9.]+)", result.stderr):
        value = float(match.group(1))
        if 0.15 < value < duration - 0.15:
            points.append(value)
    cuts = [0.0] + sorted(set(round(value, 3) for value in points)) + [round(duration, 3)]
    return [{"index": index, "start": cuts[index], "end": cuts[index+1],
             "duration": round(cuts[index+1] - cuts[index], 3)} for index in range(len(cuts)-1)]

def render_video(manifest: dict, source: Path, output: Path, work: Path) -> tuple[dict, list]:
    info = probe(source)
    shots = detect_shots(source, info["duration"])
    # Extract representative frames for storyboard/QA; final filter remains temporal.
    for shot in shots:
        sample = work / f"shot_{shot['index']:03d}_sample.png"
        midpoint = (shot["start"] + shot["end"]) / 2
        run(["ffmpeg", "-y", "-ss", str(midpoint), "-i", str(source),
             "-frames:v", "1", str(sample)])
        if sample.exists():
            with Image.open(sample) as still:
                still.convert("RGB").filter(ImageFilter.FIND_EDGES).save(
                    work / f"shot_{shot['index']:03d}_edge-preview.jpg", quality=82)
    style = manifest.get("style", "indian-comic")
    video_filter = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                    "eq=contrast=1.22:saturation=1.32:gamma=0.96,"
                    "unsharp=5:5:0.8:3:3:0.4")
    if style == "ink":
        video_filter += ",edgedetect=low=0.08:high=0.22"
    elif style == "soft":
        video_filter = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                        "eq=contrast=1.08:saturation=1.12,boxblur=1:1")
    command = ["ffmpeg", "-y", "-i", str(source), "-vf", video_filter, "-r", "30",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
    if info["has_audio"] and manifest.get("preserve_audio", True):
        command += ["-c:a", "aac", "-b:a", "128k", "-af", "aresample=async=1"]
    else:
        command += ["-an"]
    command += ["-movflags", "+faststart", str(output)]
    run(command)
    return info, shots

def quality(path: Path, expected_duration: float) -> dict:
    info = probe(path)
    if path.stat().st_size < 2048:
        raise ValueError("Output MP4 is unexpectedly small")
    if abs(info["duration"] - expected_duration) > max(1.0, expected_duration * 0.08):
        raise ValueError("Output duration differs from expected timeline")
    if info["width"] != 1080 or info["height"] != 1920:
        raise ValueError("Output is not 1080x1920")
    return {"passed": True, "duration_seconds": round(info["duration"], 3),
            "width": info["width"], "height": info["height"],
            "audio_present": info["has_audio"], "file_bytes": path.stat().st_size,
            "checks": ["ffprobe video stream", "1080x1920 dimensions",
                       "duration tolerance", "non-empty MP4"]}

def render(manifest: dict, outdir: Path) -> dict:
    validate_manifest(manifest)
    mode = manifest["mode"]
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / "frames"
    work.mkdir(exist_ok=True)
    output = outdir / "2d-trend-output.mp4"
    captions = []
    if mode == "topic":
        duration, captions = make_topic_frames(manifest, work)
        run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(work / "frame_%05d.png"),
             "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(output)])
        source_info = {"mode": "topic", "duration": duration, "has_audio": False}
        shots = [{"index": index, "start": item["start"], "end": item["end"],
                  "duration": round(item["end"] - item["start"], 3)}
                 for index, item in enumerate(captions)]
    else:
        media_path = str(manifest.get("media_path", "")).strip()
        if media_path and Path(media_path).is_file():
            source = Path(media_path)
        else:
            media_url = str(manifest.get("media_url", ""))
            if not media_url:
                raise ValueError("Video mode needs media_path or media_url")
            with tempfile.TemporaryDirectory(prefix="2dtrend-source-") as temp_dir:
                source = Path(temp_dir) / "source-video"
                download(media_url, source)
                source_info, shots = render_video(manifest, source, output, work)
        if media_path and Path(media_path).is_file():
            source_info, shots = render_video(manifest, source, output, work)
        duration = source_info["duration"]
        captions = []
    if mode == "video" and not validate_timeline(shots, duration):
        raise ValueError("Detected shot timeline is not contiguous")
    report = quality(output, duration)
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (outdir / "shots.json").write_text(json.dumps(shots, indent=2), encoding="utf-8")
    (outdir / "captions.json").write_text(json.dumps(
        {"timing": "phrase-level", "items": captions}, indent=2), encoding="utf-8")
    (outdir / "quality-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (outdir / "render.log").write_text(json.dumps(
        {"source": source_info, "shots": len(shots), "output": str(output)}, indent=2), encoding="utf-8")
    run(["ffmpeg", "-y", "-i", str(output), "-frames:v", "1", str(outdir / "poster.jpg")])
    return {"output": str(output), "quality": report, "shots": len(shots)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="artifacts")
    args = parser.parse_args()
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        print(json.dumps(render(manifest, Path(args.out)), indent=2))
    except Exception as exc:
        print(f"RENDER FAILED: {exc}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()
