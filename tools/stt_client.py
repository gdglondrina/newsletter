"""
Speech-to-text client supporting multiple providers (OpenAI Whisper, etc.).
"""

import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .error_handler import retry_with_backoff, TransientError, FatalError

logger = logging.getLogger(__name__)

# Maximum file size for most STT APIs (25MB)
MAX_FILE_SIZE_MB = 25


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    video_id: str
    transcript: str
    language: str
    duration: float
    cost: float


class BaseSTTProvider(ABC):
    """Abstract base class for speech-to-text providers."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: str = 'pt',
        response_format: str = 'text'
    ) -> TranscriptionResult:
        """Transcribe an audio file."""
        pass

    @abstractmethod
    def estimate_cost(self, audio_duration_seconds: float) -> float:
        """Estimate transcription cost based on audio duration."""
        pass

    def _check_file_size(self, audio_path: Path, max_size_mb: float = MAX_FILE_SIZE_MB) -> None:
        """Check if file size is within API limits."""
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise FatalError(
                f"Audio file too large ({file_size_mb:.1f}MB). "
                f"Maximum size is {max_size_mb}MB. "
                "Consider splitting the audio or using a lower quality."
            )

    def _extract_video_id(self, audio_path: Path) -> str:
        """Extract video ID from filename."""
        return audio_path.stem


class OpenAISTTProvider(BaseSTTProvider):
    """OpenAI Whisper API provider."""

    COST_PER_MINUTE = 0.006
    DEFAULT_MODEL = "whisper-1"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise FatalError("OPENAI_API_KEY not set")

        self.model = model or self.DEFAULT_MODEL

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise FatalError("openai package not installed")

        logger.info(f"Initialized OpenAI STT with model: {self.model}")

    def estimate_cost(self, audio_duration_seconds: float) -> float:
        minutes = audio_duration_seconds / 60
        return minutes * self.COST_PER_MINUTE

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def transcribe(
        self,
        audio_path: str,
        language: str = 'pt',
        response_format: str = 'text'
    ) -> TranscriptionResult:
        path = Path(audio_path)
        if not path.exists():
            raise FatalError(f"Audio file not found: {audio_path}")

        self._check_file_size(path)
        video_id = self._extract_video_id(path)

        logger.info(f"Transcribing: {audio_path}")

        try:
            with open(path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    response_format=response_format
                )

            if response_format == 'text':
                transcript = response
            else:
                transcript = response.text if hasattr(response, 'text') else str(response)

            # Rough estimate: 1MB ≈ 1 minute for compressed audio
            file_size_mb = path.stat().st_size / (1024 * 1024)
            estimated_duration = file_size_mb * 60

            cost = self.estimate_cost(estimated_duration)

            logger.info(f"Transcription complete. Estimated cost: ${cost:.4f}")

            return TranscriptionResult(
                video_id=video_id,
                transcript=transcript,
                language=language,
                duration=estimated_duration,
                cost=cost
            )

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, e: Exception):
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str:
            raise TransientError(f"OpenAI STT rate limit: {e}")
        elif "unauthorized" in error_str or "401" in error_str:
            raise FatalError(f"Invalid OpenAI API key: {e}")
        elif "timeout" in error_str:
            raise TransientError(f"OpenAI STT timeout: {e}")
        else:
            raise TransientError(f"OpenAI STT error: {e}")


class FasterWhisperSTTProvider(BaseSTTProvider):
    """Local Faster Whisper provider (runs on CPU or GPU, no API cost)."""

    DEFAULT_SIZE = "medium"
    DEFAULT_DEVICE = "cpu"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.model_size = os.getenv('FASTER_WHISPER_SIZE', self.DEFAULT_SIZE)
        self.device = os.getenv('FASTER_WHISPER_DEVICE', self.DEFAULT_DEVICE)

        try:
            from faster_whisper import WhisperModel
            self.whisper_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8"
            )
        except ImportError:
            raise FatalError("faster-whisper package not installed")

        logger.info(
            f"Initialized Faster Whisper: size={self.model_size}, device={self.device}"
        )

    def estimate_cost(self, audio_duration_seconds: float) -> float:
        return 0.0

    def transcribe(
        self,
        audio_path: str,
        language: str = 'pt',
        response_format: str = 'text'
    ) -> TranscriptionResult:
        path = Path(audio_path)
        if not path.exists():
            raise FatalError(f"Audio file not found: {audio_path}")

        video_id = self._extract_video_id(path)

        logger.info(f"Transcribing with Faster Whisper: {audio_path}")

        try:
            segments, info = self.whisper_model.transcribe(
                str(path),
                beam_size=5,
                language=language
            )

            transcript = " ".join(segment.text.strip() for segment in segments)
            duration = info.duration

            logger.info(
                f"Transcription complete. "
                f"Language: {info.language} (prob={info.language_probability:.2f}), "
                f"duration: {duration:.1f}s"
            )

            return TranscriptionResult(
                video_id=video_id,
                transcript=transcript,
                language=info.language,
                duration=duration,
                cost=0.0
            )

        except Exception as e:
            raise FatalError(f"Faster Whisper transcription failed: {e}")


class STTClient:
    """Speech-to-text client supporting multiple providers."""

    _IMPLEMENTATIONS = {
        'faster-whisper': FasterWhisperSTTProvider,
        'whisper': OpenAISTTProvider,
    }

    DEFAULT_MODEL = "whisper-1"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize STT client.

        Args:
            model: Model name (e.g., 'whisper-1').
                   Defaults to TRANSCRIPT_MODEL env var or 'whisper-1'.
            api_key: API key (uses appropriate env var if not provided)
        """
        self.model = model or os.getenv('TRANSCRIPT_MODEL', self.DEFAULT_MODEL)

        impl_class = None
        model_lower = self.model.lower()
        for prefix, cls in self._IMPLEMENTATIONS.items():
            if model_lower.startswith(prefix):
                impl_class = cls
                break

        if not impl_class:
            raise FatalError(
                f"Unknown STT model: {self.model}. "
                f"Supported prefixes: {', '.join(self._IMPLEMENTATIONS.keys())}"
            )

        self._impl = impl_class(api_key, self.model)
        logger.info(f"STT client initialized: {self.model}")

    def transcribe(
        self,
        audio_path: str,
        language: str = 'pt',
        response_format: str = 'text'
    ) -> TranscriptionResult:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'pt' for Portuguese)
            response_format: Output format ('text', 'json', 'srt', 'vtt')

        Returns:
            TranscriptionResult with transcript and cost
        """
        return self._impl.transcribe(audio_path, language, response_format)

    def estimate_cost(self, audio_duration_seconds: float) -> float:
        """Estimate transcription cost based on audio duration."""
        return self._impl.estimate_cost(audio_duration_seconds)


# Backwards-compatible alias
WhisperClient = STTClient
