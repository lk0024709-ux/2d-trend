# 2D Trend Studio

A mobile-first, cloud-rendered studio for two workflows:

- **Video → 2D animation** — stylize source-video shots into an original illustrated/comic look while preserving timing, cuts, and original audio by default.
- **Topic → animated reel** — create a short script, approve it, generate scenes and voice-over, add timed captions, run visual checks, and render a vertical MP4.

## Designed for Android-only development

The project is built and maintained with **OpenAI Codex**. The user interface is intended to work in a mobile browser. Heavy rendering runs in GitHub Actions or a separately configured cloud worker; a PC and local GPU are not required.

## Current status

Repository bootstrap only. The next step is for Codex to implement the MVP described in [AGENTS.md](AGENTS.md) and [CODEX_TASK.md](CODEX_TASK.md). Do not treat this repository as a finished renderer yet.

## Planned output

- MP4, 1080×1920 for reels (configurable).
- Script, scene manifest, caption file, render log, and quality-check report.
- Demo mode that runs without paid API keys.

## Important architecture note

GitHub Actions is a batch processing environment, not a permanent web server. A production web app needs a secure way to pass media and job manifests to the worker. Do not put private video files or API keys in public GitHub repositories. Use authenticated object storage or another secure transfer mechanism for private uploads.

## Development

See [AGENTS.md](AGENTS.md) for repository-wide rules and [CODEX_TASK.md](CODEX_TASK.md) for the implementation brief.