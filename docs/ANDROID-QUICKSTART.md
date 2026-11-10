# Android quick start

1. Open the repository in GitHub on your phone.
2. Open **Actions → Cloud Render → Run workflow**.
3. Paste one of the JSON manifests below into the manifest field and start the run.
4. Open the completed run and download the `2d-trend-render-...` artifact ZIP. The MP4, poster, captions, shot manifest and quality report are inside.

## Topic reel manifest

```json
{
  "version": 1,
  "mode": "topic",
  "topic": "Three surprising facts about the moon",
  "language": "English",
  "duration_seconds": 15,
  "style": "indian-comic",
  "voice": "none",
  "script": "The moon is moving away.\nIts surface holds ancient footprints.\nA day there lasts almost a month.",
  "output": {"width": 1080, "height": 1920, "fps": 24}
}
```

## Video stylization manifest

```json
{
  "version": 1,
  "mode": "video",
  "media_url": "https://example.com/my-video.mp4",
  "style": "indian-comic",
  "preserve_audio": true,
  "output": {"width": 1080, "height": 1920, "fps": 30}
}
```

Video URL must be a direct HTTPS file URL reachable by the runner. The current worker caps source media at 100 MB and 90 seconds. Do not put passwords, signed URLs with long-lived secrets, or access tokens in public workflow inputs. For private footage, configure a private object-storage handoff and short-lived credentials in Actions secrets before using it.

## Current capabilities and limitations

- Topic mode renders an animated typography/shape reel with phrase-level caption timing. It does not synthesize narration in this MVP.
- Video mode probes media, detects scene boundaries for a shot manifest, applies a deterministic FFmpeg comic-like treatment and retains original audio by default. This is a stylized filter, not generative redraw or face reconstruction.
- Optional image-generation and TTS providers are intentionally not wired until their current official APIs, credentials, data handling and billing are configured. Never expose provider keys to the browser.
- GitHub Actions is a batch worker, not a permanent web server. Workflow artifacts expire after 7 days in the manual render workflow (CI artifacts after 3 days).
- workflow_dispatch inputs are text fields, not a secure large-file upload service. Use private object storage for confidential or large media.
- Phrase-level captions are explicitly labelled; word-level alignment is not implemented.

## Local development (optional)

The owner can use GitHub Codespaces or another cloud dev environment; no local PC is required.

```sh
npm install
npm run build
python -m pip install -r worker/requirements.txt
python -m unittest worker.test_worker -v
```

FFmpeg and FFprobe are required for rendering. The GitHub Actions runners install them in the workflow.
