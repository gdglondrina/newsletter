"""
YouTube audio downloader using yt-dlp.
"""

import os
import re
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .error_handler import retry_with_backoff, TransientError, FatalError
from .file_utils import ensure_directory

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Video metadata."""
    video_id: str
    title: str
    duration: float  # seconds
    channel: str
    upload_date: str
    url: str


@dataclass
class DownloadResult:
    """Result of audio download."""
    video_id: str
    title: str
    audio_path: str
    duration: float
    format: str


class YouTubeDownloader:
    """YouTube audio downloader using yt-dlp."""

    # Regex pattern for YouTube video IDs
    VIDEO_ID_PATTERN = re.compile(
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})'
    )

    def __init__(self, output_dir: str = 'temp/audio'):
        """
        Initialize the downloader.

        Args:
            output_dir: Directory to save downloaded audio files
        """
        self.output_dir = Path(output_dir)
        ensure_directory(self.output_dir)

    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is a valid YouTube video URL.

        Args:
            url: URL to validate

        Returns:
            True if valid YouTube URL
        """
        return bool(self.VIDEO_ID_PATTERN.search(url))

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL.

        Args:
            url: YouTube URL

        Returns:
            Video ID or None if invalid
        """
        match = self.VIDEO_ID_PATTERN.search(url)
        return match.group(1) if match else None

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def get_video_info(self, url: str) -> VideoInfo:
        """
        Get video metadata without downloading.

        Args:
            url: YouTube video URL

        Returns:
            VideoInfo object with metadata

        Raises:
            FatalError: If URL is invalid or video not found
            TransientError: If network error occurs
        """
        if not self.validate_url(url):
            raise FatalError(f"Invalid YouTube URL: {url}")

        video_id = self.extract_video_id(url)

        try:
            result = subprocess.run(
                [
                    'yt-dlp',
                    '--dump-json',
                    '--no-download',
                    url
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "Video unavailable" in error_msg or "Private video" in error_msg:
                    raise FatalError(f"Video not available: {url}")
                raise TransientError(f"yt-dlp error: {error_msg}")

            info = json.loads(result.stdout)

            return VideoInfo(
                video_id=video_id,
                title=info.get('title', 'Unknown'),
                duration=info.get('duration', 0),
                channel=info.get('channel', 'Unknown'),
                upload_date=info.get('upload_date', ''),
                url=url
            )

        except subprocess.TimeoutExpired:
            raise TransientError(f"Timeout getting video info: {url}")
        except json.JSONDecodeError as e:
            raise TransientError(f"Failed to parse video info: {e}")
        except FileNotFoundError:
            raise FatalError("yt-dlp not installed. Run: brew install yt-dlp")

    @retry_with_backoff(max_retries=3, initial_delay=5.0)
    def download_audio(
        self,
        url: str,
        format: str = 'm4a',
        quality: str = 'bestaudio'
    ) -> DownloadResult:
        """
        Download audio from YouTube video.

        Args:
            url: YouTube video URL
            format: Output audio format (m4a, mp3, etc.)
            quality: Audio quality selector

        Returns:
            DownloadResult with file path and metadata

        Raises:
            FatalError: If URL invalid or video unavailable
            TransientError: If download fails due to network
        """
        if not self.validate_url(url):
            raise FatalError(f"Invalid YouTube URL: {url}")

        video_id = self.extract_video_id(url)
        output_path = self.output_dir / f"{video_id}.{format}"

        logger.info(f"Downloading audio from: {url}")

        try:
            # Get video info first
            info = self.get_video_info(url)

            # Download audio
            result = subprocess.run(
                [
                    'yt-dlp',
                    '-x',  # Extract audio
                    '--audio-format', format,
                    '--audio-quality', '0',  # Best quality
                    '-o', str(output_path),
                    '--no-playlist',  # Don't download playlists
                    '--no-warnings',
                    url
                ],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes max for long videos
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                raise TransientError(f"Download failed: {error_msg}")

            # Verify file exists
            if not output_path.exists():
                # yt-dlp might add extension, try to find the file
                possible_files = list(self.output_dir.glob(f"{video_id}.*"))
                if possible_files:
                    output_path = possible_files[0]
                else:
                    raise TransientError(f"Downloaded file not found: {output_path}")

            logger.info(f"Downloaded: {output_path}")

            return DownloadResult(
                video_id=video_id,
                title=info.title,
                audio_path=str(output_path),
                duration=info.duration,
                format=format
            )

        except subprocess.TimeoutExpired:
            raise TransientError(f"Timeout downloading: {url}")
        except FileNotFoundError:
            raise FatalError("yt-dlp not installed. Run: brew install yt-dlp")
