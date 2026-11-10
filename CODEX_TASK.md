# Codex implementation brief — 2D Trend Studio

You are OpenAI Codex working inside this repository. Read `AGENTS.md` first and follow it.

## Goal
Turn this empty/bootstrap repository into a working, testable MVP for a mobile-first 2D animation and reel generator. The owner uses Android and has no PC. Do not build a workflow that depends on Claude Code, a local desktop, or a local GPU.

## First actions
1. Inspect the repository and current branch. Preserve existing files.
2. Create a feature branch named `codex/mvp-studio` (or a safe unique equivalent).
3. Propose a concise implementation plan, then execute it without waiting unless a blocking decision is unavoidable.
4. Keep commits focused and open a PR; do not merge it.

## Required MVP

### A. Mobile web interface
- Build a responsive phone-first dashboard.
- Two workflow cards/tabs: `Video to 2D Animation` and `Topic to Animated Reel`.
- Topic mode: topic, language, target duration, visual style, voice choice; script preview/edit/approval before render.
- Video mode: source media URL or upload integration abstraction, target style, preserve-original-audio toggle.
- Show job status, progress stages, errors, downloadable artifact links, and render metadata.
- Use a demo mode if secure upload or cloud backend is not configured. Do not fake successful rendering.

### B. Shared job contract
- Define typed/validated job manifest for both modes.
- Validate allowed formats, file size, duration, resolution, and URL schemes.
- Explicit job lifecycle: queued, validating, scripting, awaiting_approval, generating_assets, rendering, quality_check, completed, failed, cancelled.
- Store logs and stage progress without leaking secrets.

### C. Python media worker
- Probe input using FFprobe.
- Detect scene boundaries and create a deterministic shot manifest.
- Sample representative frames per shot.
- Implement a provider interface for original stylized frame generation. Include a deterministic mock provider for CI/demo.
- Rebuild the timeline while preserving source cuts and timing; retain original audio by default.
- Topic mode: generate a structured scene manifest and render animated scenes with typography, shapes, transitions, and optional generated stills.
- Generate captions. If word-level alignment is unavailable, use an explicitly labelled phrase-level fallback; do not claim word-level precision.
- Render vertical MP4 with FFmpeg and create a poster/thumbnail.
- Produce a machine-readable quality report (duration, dimensions, audio presence, black-frame/empty-output checks where feasible).

### D. Voice and AI providers
- Define provider interfaces for TTS and image generation.
- Provide a no-key mock/demo provider.
- Optional OpenAI and ElevenLabs adapters must read credentials from environment variables available only to the worker. Never send keys to frontend.
- User may supply their own recorded narration.
- Do not hardcode model names or assume a provider's current API shape without checking official docs during implementation.

### E. GitHub Actions
- Add CI for lint/typecheck/unit tests and a no-secret demo render.
- Add a manual render workflow with validated inputs and explicit safety limits.
- Do not expose secrets to forked pull requests.
- Upload output MP4, manifest, captions, logs, and quality report as workflow artifacts.
- Document artifact retention and GitHub Actions runtime/storage limitations.
- Do not treat workflow_dispatch text fields as a secure arbitrary large-file upload. Use secure object storage for private source videos.

### F. Quality and tests
- Unit tests for manifest validation, timeline/cut preservation, caption timing, job state transitions, and output validation.
- CI must pass without paid credentials.
- Include a short synthetic fixture generated in code; do not commit copyrighted footage or large binary assets.

## Design direction
- Modern creator studio, dark-neutral base with clear high-contrast controls.
- Mobile-first layout, large touch targets, clear progress.
- Indian comic / cel-shaded visual preset as one option; avoid copying any real actor's face or a living artist's signature style.
- 9:16 default, configurable 1080×1920 output.
- Keep UI polished but prioritize a reliable pipeline over decorative complexity.

## Acceptance criteria
- Fresh clone can install dependencies and run tests using documented commands.
- Demo topic reel can render end-to-end in CI without paid APIs.
- Demo video pipeline can process a generated synthetic clip, produce an output MP4, and preserve audio/timing when the fixture contains audio.
- The UI clearly distinguishes demo from real cloud render.
- Documentation explains Android usage, GitHub setup, required secrets, secure media handoff, limitations, and troubleshooting.
- No secrets, user uploads, or generated media are committed.

## Final response
Report the PR URL, implemented features, exact test commands/results, any GitHub secrets still required, and known limitations. Never claim an unrun test passed.
