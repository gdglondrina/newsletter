"""
OpenAI Whisper API client for audio transcription.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from .error_handler import retry_with_backoff, TransientError, FatalError

logger = logging.getLogger(__name__)

# Whisper API cost per minute (as of 2024)
WHISPER_COST_PER_MINUTE = 0.006

# Maximum file size for Whisper API (25MB)
MAX_FILE_SIZE_MB = 25


@dataclass
class TranscriptionResult:
    """Result of audio transcription."""
    video_id: str
    transcript: str
    language: str
    duration: float
    cost: float


class WhisperClient:
    """OpenAI Whisper API client for audio transcription."""

    DEFAULT_MODEL = "whisper-1"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the Whisper client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Whisper model to use (defaults to TRANSCRIPT_MODEL env var or 'whisper-1')
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise FatalError("OPENAI_API_KEY not set in environment")

        self.model = model or os.getenv('TRANSCRIPT_MODEL', self.DEFAULT_MODEL)
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"Initialized Whisper client with model: {self.model}")

    def estimate_cost(self, audio_duration_seconds: float) -> float:
        """
        Estimate transcription cost based on audio duration.

        Args:
            audio_duration_seconds: Duration of audio in seconds

        Returns:
            Estimated cost in USD
        """
        minutes = audio_duration_seconds / 60
        return minutes * WHISPER_COST_PER_MINUTE

    def _check_file_size(self, audio_path: Path) -> None:
        """Check if file size is within Whisper API limits."""
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise FatalError(
                f"Audio file too large ({file_size_mb:.1f}MB). "
                f"Maximum size is {MAX_FILE_SIZE_MB}MB. "
                "Consider splitting the audio or using a lower quality."
            )

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def transcribe(
        self,
        audio_path: str,
        language: str = 'pt',
        response_format: str = 'text'
    ) -> TranscriptionResult:
        """
        Transcribe audio file using Whisper API.

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'pt' for Portuguese)
            response_format: Output format ('text', 'json', 'srt', 'vtt')

        Returns:
            TranscriptionResult with transcript and cost

        Raises:
            FatalError: If file not found or too large
            TransientError: If API call fails
        """
        path = Path(audio_path)
        if not path.exists():
            raise FatalError(f"Audio file not found: {audio_path}")

        self._check_file_size(path)

        # Extract video ID from filename
        video_id = path.stem

        logger.info(f"Transcribing: {audio_path}")

        try:
            with open(path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    response_format=response_format
                )

            # Get transcript text
            if response_format == 'text':
                transcript = response
            else:
                transcript = response.text if hasattr(response, 'text') else str(response)

            # Estimate duration from file (rough estimate based on file size)
            # For accurate duration, we'd need to parse the audio file
            file_size_mb = path.stat().st_size / (1024 * 1024)
            # Rough estimate: 1MB ≈ 1 minute for compressed audio
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
            error_str = str(e).lower()

            if "rate limit" in error_str or "429" in error_str:
                raise TransientError(f"Rate limit exceeded: {e}")
            elif "unauthorized" in error_str or "401" in error_str:
                raise FatalError(f"Invalid API key: {e}")
            elif "timeout" in error_str:
                raise TransientError(f"Request timeout: {e}")
            else:
                raise TransientError(f"Transcription failed: {e}")
