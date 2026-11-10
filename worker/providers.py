"""Provider contracts and deterministic no-key implementations.

Real provider adapters must be implemented server-side and must read credentials
from environment variables. They must never be imported by the browser bundle.
"""
from __future__ import annotations
from pathlib import Path
from typing import Protocol
from PIL import Image, ImageFilter, ImageOps

class ImageProvider(Protocol):
    def stylize_frame(self, source: Path, destination: Path, style: str) -> None: ...

class TTSProvider(Protocol):
    def synthesize(self, text: str, destination: Path, language: str) -> None: ...

class MockImageProvider:
    """Deterministic local comic-like frame treatment for tests and previews."""
    def stylize_frame(self, source: Path, destination: Path, style: str="indian-comic") -> None:
        with Image.open(source) as image:
            frame=ImageOps.posterize(image.convert("RGB"),4).filter(ImageFilter.EDGE_ENHANCE)
            frame.save(destination,quality=88)

class NoVoiceProvider:
    """Explicit no-audio provider; it never claims to synthesize speech."""
    def synthesize(self, text: str, destination: Path, language: str="English") -> None:
        raise RuntimeError("No TTS provider configured. Select no voice or configure a server-side TTS adapter.")

def configured_tts_provider() -> TTSProvider:
    if os.environ.get("ELEVENLABS_API_KEY"):
        raise RuntimeError("ElevenLabs credentials detected, but no adapter is enabled. Add a reviewed server-side adapter before use.")
    if os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OpenAI credentials detected, but no adapter is enabled. Add a reviewed server-side adapter before use.")
    return NoVoiceProvider()

import os
