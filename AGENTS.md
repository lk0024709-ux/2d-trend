# AGENTS.md — 2D Trend Studio

## Mission
Build a mobile-first, cloud-rendered 2D animation and short-form video studio. The owner works from Android and does not have a PC. Use OpenAI Codex as the coding agent; do not require Claude Code.

## Product modes
1. **Video → 2D animation**: accept a source video, detect shots, sample frames, create an original illustrated/cel-shaded Indian-comic treatment (do not trace or reproduce real actors' exact faces), preserve source timing, cuts and audio where practical, then render MP4.
2. **Topic → animated reel**: topic → script draft and approval → scene plan/storyboard → voice (user recording or configured TTS) → word-timed captions → animated scenes → quality checks → MP4 and social caption/hashtags.

## Non-negotiable constraints
- Android-first controls; all heavy rendering runs in GitHub Actions or another explicitly configured cloud worker. Never require a local desktop, local Claude Code, or local GPU.
- Keep API keys out of source, browser bundles, prompts, logs, artifacts, and Git. Use GitHub Actions secrets / server-side secrets only. Provide .env.example with placeholders only.
- Never claim an output exists until the workflow has actually rendered and uploaded it.
- Respect GitHub Actions limits. Use short demo fixtures in CI; full user videos are dispatched as cloud jobs and validate size, duration, format, and available runner time first.
- Make processing resumable and report actionable job states/errors.
- Do not commit generated videos, user uploads, model weights, or secrets.
- Preserve source audio and scene cuts by default in video-to-animation mode; let users opt into replacement audio.
- Never imitate a living artist or reproduce a real person's face. For source-video mode, stylize scenes while avoiding identity replication.
- Use accessible, responsive UI suitable for a phone screen.
- Pin dependencies and use reproducible builds where practical.

## Engineering workflow
1. Inspect the existing repository before editing. It may be empty on first setup.
2. Implement in small, testable phases. Do not replace working code blindly.
3. Prefer TypeScript for the web interface and Python for media orchestration; use FFmpeg for media operations. Evaluate HyperFrames/Remotion only after checking current compatibility and licensing; do not assume either provides generative frame stylization by itself.
4. Separate the UI, job orchestration, media pipeline, providers, and tests.
5. Provide mock/demo providers so CI can run without paid API keys.
6. Add unit tests for validation, shot manifests, captions, timeline math, and job state transitions.
7. Add a GitHub Actions workflow for lint/test and a manually dispatched render workflow. Never expose secrets to pull-request code.
8. After each phase, run available checks and summarize changed files, test results, setup required, and known limitations.

## Suggested architecture
- `apps/web`: mobile-first web app / job dashboard.
- `packages/shared`: shared schemas and validation.
- `worker/`: Python media pipeline and provider adapters.
- `scripts/`: local/CI helper scripts.
- `.github/workflows/`: CI and manual cloud render workflow.
- `docs/`: architecture, Android usage, secrets, and operations.

## Initial delivery (MVP)
- Responsive web UI with two clearly separated workflows.
- Topic-reel script editor/approval step and source-video URL/upload guidance.
- Strict input validation and job manifest schema.
- Python worker that can create a deterministic demo reel without paid services, plus optional provider interfaces for image generation and TTS.
- Video processing pipeline that probes media, detects/splits shots, samples frames, applies a replaceable stylization provider, then remuxes original audio and timing.
- Word-level captions: use Whisper alignment when configured; otherwise clearly label sentence/phrase timing fallback.
- Manual GitHub Actions workflow accepting a validated job manifest or media URL; secrets read only from GitHub Actions secrets.
- Artifact upload and clear run summary.
- Documentation explaining that GitHub Actions is a batch worker, not a permanent web server, and that private media needs secure object storage or a suitable authenticated transfer path.

## Codex operating instructions
Start by checking repository status, files, branches, and existing workflows. Then implement the MVP in a feature branch and open a pull request; do not merge without the owner's approval. If the repository is empty, initialize a clean, minimal project. Do not ask the owner to install desktop software. Ask only when a genuinely blocking external choice or credential is needed; otherwise use safe mock defaults.
