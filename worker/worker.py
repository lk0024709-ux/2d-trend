#!/usr/bin/env python3
"""Deterministic 2D Trend render worker. FFmpeg and FFprobe must be on PATH."""
from __future__ import annotations
import argparse, ipaddress, json, math, os, re, socket, subprocess, sys, urllib.request\nfrom urllib.parse import urlparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS = 90
W, H, FPS = 720, 1280, 24

def run(cmd: list[str], capture: bool=False) -> str:
    p = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE if capture else subprocess.DEVNULL, stderr=subprocess.PIPE)
    return p.stdout if capture else ""

def probe(path: Path) -> dict:
    raw = run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],True)
    data=json.loads(raw); streams=data.get("streams",[])
    video=next((s for s in streams if s.get("codec_type")=="video"),None)
    if not video: raise ValueError("Input has no video stream")
    duration=float(data.get("format",{}).get("duration",0))
    if duration<=0 or duration>MAX_SECONDS: raise ValueError(f"Video duration must be between 0 and {MAX_SECONDS} seconds")
    return {"duration":duration,"width":int(video["width"]),"height":int(video["height"]),"has_audio":any(s.get("codec_type")=="audio" for s in streams)}

def download(url: str, target: Path) -> None:
    if not url.startswith("https://"): raise ValueError("Only HTTPS media URLs are allowed")
    req=urllib.request.Request(url,headers={"User-Agent":"2DTrendStudio/0.1"})
    total=0
    with opener.open(req,timeout=30) as response, target.open("wb") as out:
        if response.headers.get("Content-Length") and int(response.headers["Content-Length"])>MAX_BYTES: raise ValueError("Media exceeds 100 MB")
        while True:
            chunk=response.read(1024*1024)
            if not chunk: break
            total+=len(chunk)
            if total>MAX_BYTES: raise ValueError("Media exceeds 100 MB")
            out.write(chunk)

def font(size: int):
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(name).exists(): return ImageFont.truetype(name,size)
    return ImageFont.load_default()

def wrap(draw, text: str, fnt, max_width: int):
    words=text.split(); lines=[]; line=""
    for word in words:
        test=(line+" "+word).strip()
        if draw.textbbox((0,0),test,font=fnt)[2] > max_width and line:
            lines.append(line); line=word
        else: line=test
    if line: lines.append(line)
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
    if manifest.get("version") != 1: raise ValueError("Unsupported manifest version")
    if manifest.get("mode") not in ("topic", "video"): raise ValueError("mode must be topic or video")
    output=manifest.get("output", {})
    if output and (output.get("width",1080)!=1080 or output.get("height",1920)!=1920):
        raise ValueError("MVP output must be 1080x1920")
    if manifest["mode"]=="topic":
        if not 4 <= len(str(manifest.get("topic","")).strip()) <= 500: raise ValueError("Topic must contain 4-500 characters")
        if not 5 <= int(manifest.get("duration_seconds",15)) <= 60: raise ValueError("Topic duration must be 5-60 seconds")
        if len(str(manifest.get("script",""))) > 5000: raise ValueError("Script must be 5000 characters or fewer")
    else:
        url=str(manifest.get("media_url",""))
        if not manifest.get("media_path") and not url.startswith("https://"): raise ValueError("Video mode requires an HTTPS media_url")

def transition_job(current: str, next_state: str) -> str:
    if next_state not in ALLOWED_STATES.get(current, set()): raise ValueError(f"Invalid job transition: {current} -> {next_state}")
    return next_state

def validate_timeline(shots: list[dict], duration: float) -> bool:
    if not shots or abs(float(shots[0]["start"])) > 0.01: return False
    cursor=0.0
    for shot in shots:
        start=float(shot["start"]); end=float(shot["end"])
        if abs(start-cursor)>0.02 or end<=start: return False
        cursor=end
    return abs(cursor-duration)<=0.05

def make_topic_frames(manifest: dict, outdir: Path) -> tuple[float,list[dict]]:
    duration=max(5,min(int(manifest.get("duration_seconds",15)),60)); total=duration*FPS
    topic=str(manifest["topic"]); script=str(manifest.get("script") or topic)
    chunks=[x.strip() for x in re.split(r"(?<=[.!?।])\s+|\n+",script) if x.strip()] or [topic]
    captions=[]; scene_len=duration/len(chunks)
    for i,chunk in enumerate(chunks):
        captions.append({"text":chunk,"start":round(i*scene_len,3),"end":round((i+1)*scene_len,3),"timing":"phrase-level"})
    palette=[(25,34,57),(50,30,65),(25,58,61),(63,40,35)]
    for frame in range(total):
        t=frame/FPS; idx=min(len(chunks)-1,int(t/scene_len)); local=(t-idx*scene_len)/scene_len
        bg=palette[idx%len(palette)]
        im=Image.new("RGB",(W,H),bg); d=ImageDraw.Draw(im)
        # Animated graphic elements: moving rings, accent bars and kinetic title placement.
        cx=int(W*(.72-.12*local)); cy=int(H*(.22+.05*math.sin(t*2)))
        for radius in (90,145,205):
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=(105,139,94),width=3)
        d.rounded_rectangle((52,90,68,250),radius=8,fill=(201,255,88))
        d.text((52,300),"2D TREND / STORY",font=font(22),fill=(201,255,88))
        fnt=font(54); lines=wrap(d,chunks[idx],fnt,W-110)
        y=470-int(18*math.sin(local*math.pi))
        for line in lines[:5]:
            d.text((52,y),line,font=fnt,fill=(255,255,255),stroke_width=2,stroke_fill=(15,15,22)); y+=72
        d.text((52,1130),f"{manifest.get('language','English').upper()}  •  {idx+1:02d}/{len(chunks):02d}",font=font(18),fill=(205,205,215))
        im.save(outdir/f"frame_{frame:05d}.png",optimize=True)
    return float(duration),captions

def detect_shots(video: Path, duration: float) -> list[dict]:
    # FFmpeg emits showinfo records at scene transitions. Always include first/last boundary.
    cmd=["ffmpeg","-hide_banner","-i",str(video),"-vf","select='gt(scene,0.30)',showinfo","-an","-f","null","-"]
    p=subprocess.run(cmd,text=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    pts=[]
    for match in re.finditer(r"pts_time:([0-9.]+)",p.stderr):
        value=float(match.group(1))
        if 0.15<value<duration-0.15: pts.append(value)
    cuts=[0.0]+sorted(set(round(x,3) for x in pts))+[round(duration,3)]
    return [{"index":i,"start":cuts[i],"end":cuts[i+1],"duration":round(cuts[i+1]-cuts[i],3)} for i in range(len(cuts)-1)]

def render_video(manifest: dict, source: Path, out: Path, work: Path) -> tuple[dict,list]:
    info=probe(source); shots=detect_shots(source,info["duration"])
    # Deterministic comic-like colour treatment; audio is retained unless explicitly disabled.
    style=manifest.get("style","indian-comic")
    vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.22:saturation=1.32:gamma=0.96,unsharp=5:5:0.8:3:3:0.4"
    if style=="ink": vf+=",edgedetect=low=0.08:high=0.22"
    elif style=="soft": vf="scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.08:saturation=1.12,boxblur=1:1"
    cmd=["ffmpeg","-y","-i",str(source),"-vf",vf,"-r","30","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p"]
    if info["has_audio"] and manifest.get("preserve_audio",True): cmd += ["-c:a","aac","-b:a","128k","-af","aresample=async=1"]
    else: cmd += ["-an"]
    cmd += ["-movflags","+faststart",str(out)]; run(cmd)
    return info,shots

def quality(path: Path, expected_duration: float) -> dict:
    info=probe(path)
    if path.stat().st_size<2048: raise ValueError("Output MP4 is unexpectedly small")
    if abs(info["duration"]-expected_duration)>max(1.0,expected_duration*0.08): raise ValueError("Output duration differs from expected timeline")
    if info["width"]!=1080 or info["height"]!=1920: raise ValueError("Output is not 1080x1920")
    return {"passed":True,"duration_seconds":round(info["duration"],3),"width":info["width"],"height":info["height"],"audio_present":info["has_audio"],"file_bytes":path.stat().st_size,"checks":["ffprobe video stream","1080x1920 dimensions","duration tolerance","non-empty MP4"]}

def render(manifest: dict, outdir: Path) -> dict:
    if manifest.get("version")!=1: raise ValueError("Unsupported manifest version")
    mode=manifest.get("mode")
    outdir.mkdir(parents=True,exist_ok=True); work=outdir/"frames"; work.mkdir(exist_ok=True)
    output=outdir/"2d-trend-output.mp4"; captions=[]
    if mode=="topic":
        if len(str(manifest.get("topic","")).strip())<4: raise ValueError("Topic must contain at least 4 characters")
        duration,captions=make_topic_frames(manifest,work)
        run(["ffmpeg","-y","-framerate",str(FPS),"-i",str(work/"frame_%05d.png"),"-vf","scale=1080:1920:flags=lanczos","-c:v","libx264","-preset","veryfast","-crf","24","-pix_fmt","yuv420p","-movflags","+faststart",str(output)])
        source_info={"mode":"topic","duration":duration,"has_audio":False}
        shots=[{"index":i,"start":c["start"],"end":c["end"],"duration":round(c["end"]-c["start"],3)} for i,c in enumerate(captions)]
    elif mode=="video":
        source=Path(manifest.get("media_path",""))
        if not source.exists():
            url=str(manifest.get("media_url",""))
            if not url: raise ValueError("Video mode needs media_path or media_url")
            source=outdir/"source-video"; download(url,source)
        source_info,shots=render_video(manifest,source,output,work)
        duration=source_info["duration"]
        captions=[]
        if source_info["has_audio"] and not manifest.get("preserve_audio",True): source_info["has_audio"]=False
    else: raise ValueError("mode must be topic or video")
    if mode=="video" and not validate_timeline(shots,duration): raise ValueError("Detected shot timeline is not contiguous")\n    report=quality(output,duration)
    (outdir/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    (outdir/"shots.json").write_text(json.dumps(shots,indent=2),encoding="utf-8")
    (outdir/"captions.json").write_text(json.dumps({"timing":"phrase-level","items":captions},indent=2),encoding="utf-8")
    (outdir/"quality-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    (outdir/"render.log").write_text(json.dumps({"source":source_info,"shots":len(shots),"output":str(output)},indent=2),encoding="utf-8")
    # Poster from first frame of final output.
    run(["ffmpeg","-y","-i",str(output),"-frames:v","1",str(outdir/"poster.jpg")])
    return {"output":str(output),"quality":report,"shots":len(shots)}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--manifest",required=True); parser.add_argument("--out",default="artifacts")
    args=parser.parse_args()
    try:
        manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        result=render(manifest,Path(args.out)); print(json.dumps(result,indent=2))
    except Exception as exc:
        print(f"RENDER FAILED: {exc}",file=sys.stderr); raise

if __name__=="__main__": main()
