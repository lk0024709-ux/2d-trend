# 2D Trend Studio

Mobile-first, cloud-rendered 2D reel and video stylization MVP. The UI is a lightweight web app; FFmpeg media work runs in GitHub Actions.

## Workflows
- **Topic → Animated Reel:** review and approve a script, then render an animated 9:16 typography reel with phrase-level captions.
- **Video → 2D Animation:** validate a direct HTTPS source, probe it with FFprobe, detect shot boundaries, apply a deterministic comic-style filter, and preserve original audio by default.

## Android usage
See [Android quick start](docs/ANDROID-QUICKSTART.md). Open the Render workflow from the Actions tab, paste a manifest, run it, then download the artifact ZIP.

## Development
`npm install && npm run build`
`pip install -r worker/requirements.txt && python -m unittest worker.test_worker -v`

## Honest capability boundary
The no-key MVP is deterministic and does not generate original AI artwork or narration. Image generation and TTS provider interfaces are planned extension points; add a server-side provider only after checking current official API documentation and storing credentials in GitHub Actions secrets. Never paste secrets into manifests.

GitHub Actions is a batch worker, not a permanent server. Private uploads require secure object storage. See [Android quick start](docs/ANDROID-QUICKSTART.md) for limits and details.
