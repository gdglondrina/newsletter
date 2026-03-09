#!/usr/bin/env python3
"""
Transcription step: Transcribe audio files using Whisper API.
"""

import re
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.stt_client import STTClient
from tools.file_utils import read_json, write_json, read_file, write_file, ensure_directory
from tools.error_handler import FatalError

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMP_TRANSCRIPTS_DIR = PROJECT_ROOT / "temp" / "transcripts"
CONTEXT_FILE = PROJECT_ROOT / "context" / "current_processing.json"


def parse_srt(srt_path: str) -> str:
    """
    Parse an SRT subtitle file and return text with timestamps.

    Args:
        srt_path: Path to .srt file

    Returns:
        Transcript text with timestamps
    """
    content = read_file(srt_path)

    # SRT format: index, timestamp line, text lines, blank line
    blocks = re.split(r'\n\n+', content.strip())

    lines = []
    for block in blocks:
        block_lines = block.strip().splitlines()
        if len(block_lines) < 2:
            continue

        # Find the timestamp line (contains -->)
        timestamp_line = None
        text_lines = []
        for bl in block_lines:
            if '-->' in bl:
                timestamp_line = bl
            elif timestamp_line and not re.match(r'^\d+$', bl.strip()):
                text_lines.append(bl.strip())

        if timestamp_line and text_lines:
            # Extract start time (e.g. "00:01:23,456 --> 00:01:25,789")
            start = timestamp_line.split('-->')[0].strip().replace(',', '.')
            # Remove milliseconds for readability
            start = re.sub(r'\.\d+$', '', start)
            text = ' '.join(text_lines)
            lines.append(f"[{start}] {text}")

    return '\n'.join(lines)


def transcribe_audio(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transcribe audio files from the state.
    Uses YouTube subtitles when available, falls back to STT model.

    Args:
        state: Current processing state with audio paths

    Returns:
        Updated state with transcription results
    """
    ensure_directory(TEMP_TRANSCRIPTS_DIR)

    # Lazy-init STT client only if needed
    client = None

    total_cost = state.get('total_cost', 0.0)

    for video in state.get('videos', []):
        # Check if already transcribed
        if video.get('transcript_path') and Path(video['transcript_path']).exists():
            logger.info(f"Skipping already transcribed: {video['video_id']}")
            continue

        video_id = video.get('video_id', 'unknown')
        transcript_path = TEMP_TRANSCRIPTS_DIR / f"{video_id}_transcript.txt"

        # Try YouTube subtitles first
        subtitle_path = video.get('subtitle_path')
        if subtitle_path and Path(subtitle_path).exists():
            try:
                logger.info(f"Using YouTube subtitles for: {video.get('title')}")
                transcript = parse_srt(subtitle_path)

                write_file(transcript_path, transcript)

                video['transcript_path'] = str(transcript_path)
                video['transcript_source'] = 'youtube_subs'
                video['status'] = 'transcribed'
                video['costs']['transcription'] = 0.0

                logger.info(f"Transcript from subs: {transcript_path} (free)")
                continue

            except Exception as e:
                logger.warning(f"Failed to parse subtitles for {video_id}, falling back to STT: {e}")

        # Fall back to STT model
        audio_path = video.get('audio_path')
        if not audio_path or not Path(audio_path).exists():
            logger.error(f"Audio file not found for {video_id}")
            continue

        try:
            if client is None:
                client = STTClient()

            logger.info(f"Transcribing with STT: {video.get('title')}")

            result = client.transcribe(audio_path, language='pt')

            write_file(transcript_path, result.transcript)

            video['transcript_path'] = str(transcript_path)
            video['transcript_source'] = 'stt_model'
            video['status'] = 'transcribed'
            video['costs']['transcription'] = result.cost
            total_cost += result.cost

            logger.info(f"Transcribed: {transcript_path} (${result.cost:.4f})")

        except Exception as e:
            logger.error(f"Transcription failed for {video_id}: {e}")
            video['status'] = 'transcription_failed'
            video['error'] = str(e)

    # Update state
    state['total_cost'] = total_cost
    state['current_step'] = 'summary'

    return state


def main(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for transcription.

    Args:
        state: Processing state (or load from file)

    Returns:
        Updated processing state
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load state if not provided
    if state is None:
        try:
            state = read_json(CONTEXT_FILE)
        except FileNotFoundError:
            print("Error: No processing state found. Run extract_audio.py first.")
            sys.exit(1)

    # Check current step
    if state.get('current_step') not in ['transcription', 'audio_extraction']:
        logger.warning(f"Unexpected step: {state.get('current_step')}")

    # Run transcription
    state = transcribe_audio(state)

    # Save state
    write_json(CONTEXT_FILE, state)

    # Print summary
    transcribed = sum(1 for v in state['videos'] if v.get('status') == 'transcribed')
    print(f"\nTranscription complete:")
    print(f"  - {transcribed}/{len(state['videos'])} videos transcribed")
    print(f"  - Total cost so far: ${state['total_cost']:.4f}")

    return state


if __name__ == "__main__":
    main()
