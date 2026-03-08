#!/usr/bin/env python3
"""
Audio extraction step: Download audio from YouTube videos.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.youtube_downloader import YouTubeDownloader, DownloadResult
from tools.file_utils import read_json, write_json, ensure_directory
from tools.error_handler import FatalError

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMP_AUDIO_DIR = PROJECT_ROOT / "temp" / "audio"
CONTEXT_FILE = PROJECT_ROOT / "context" / "current_processing.json"


def extract_audio(video_urls: List[str], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Download audio from YouTube videos.

    Args:
        video_urls: List of YouTube video URLs
        state: Current processing state

    Returns:
        Updated state with download results
    """
    ensure_directory(TEMP_AUDIO_DIR)
    downloader = YouTubeDownloader(output_dir=str(TEMP_AUDIO_DIR))

    results = []
    errors = []

    for url in video_urls:
        # Check if already processed
        existing = next(
            (v for v in state.get('videos', []) if v['url'] == url and v.get('audio_path')),
            None
        )
        if existing:
            logger.info(f"Skipping already downloaded: {url}")
            results.append(existing)
            continue

        try:
            # Validate URL
            if not downloader.validate_url(url):
                raise FatalError(f"Invalid YouTube URL: {url}")

            # Get video info first
            info = downloader.get_video_info(url)
            logger.info(f"Processing: {info.title} ({info.duration:.0f}s)")

            # Download audio
            result = downloader.download_audio(url)

            video_data = {
                'url': url,
                'video_id': result.video_id,
                'title': result.title,
                'duration': result.duration,
                'audio_path': result.audio_path,
                'status': 'audio_extracted',
                'costs': {}
            }
            results.append(video_data)
            logger.info(f"Downloaded: {result.audio_path}")

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            errors.append({
                'url': url,
                'error': str(e)
            })

    # Update state
    state['videos'] = results
    state['errors'] = state.get('errors', []) + errors
    state['current_step'] = 'transcription'

    return state


def main(video_urls: List[str] = None) -> Dict[str, Any]:
    """
    Main entry point for audio extraction.

    Args:
        video_urls: List of YouTube URLs (or from command line)

    Returns:
        Updated processing state
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get URLs from args if not provided
    if video_urls is None:
        if len(sys.argv) < 2:
            print("Usage: python extract_audio.py <url1> [url2] ...")
            sys.exit(1)
        video_urls = sys.argv[1:]

    # Load or initialize state
    try:
        state = read_json(CONTEXT_FILE)
    except FileNotFoundError:
        state = {
            'session_id': '',
            'status': 'in_progress',
            'current_step': 'audio_extraction',
            'videos': [],
            'total_cost': 0.0
        }

    # Run extraction
    state = extract_audio(video_urls, state)

    # Save state
    ensure_directory(CONTEXT_FILE.parent)
    write_json(CONTEXT_FILE, state)

    print(f"\nAudio extraction complete:")
    print(f"  - {len(state['videos'])} videos processed")
    if state.get('errors'):
        print(f"  - {len(state['errors'])} errors")

    return state


if __name__ == "__main__":
    main()
