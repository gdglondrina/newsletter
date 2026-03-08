#!/usr/bin/env python3
"""
Transcription step: Transcribe audio files using Whisper API.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.stt_client import STTClient
from tools.file_utils import read_json, write_json, write_file, ensure_directory
from tools.error_handler import FatalError

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMP_TRANSCRIPTS_DIR = PROJECT_ROOT / "temp" / "transcripts"
CONTEXT_FILE = PROJECT_ROOT / "context" / "current_processing.json"


def transcribe_audio(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transcribe audio files from the state.

    Args:
        state: Current processing state with audio paths

    Returns:
        Updated state with transcription results
    """
    ensure_directory(TEMP_TRANSCRIPTS_DIR)
    client = STTClient()

    total_cost = state.get('total_cost', 0.0)

    for video in state.get('videos', []):
        # Check if already transcribed
        if video.get('transcript_path') and Path(video['transcript_path']).exists():
            logger.info(f"Skipping already transcribed: {video['video_id']}")
            continue

        audio_path = video.get('audio_path')
        if not audio_path or not Path(audio_path).exists():
            logger.error(f"Audio file not found for {video.get('video_id', 'unknown')}")
            continue

        try:
            logger.info(f"Transcribing: {video['title']}")

            # Transcribe
            result = client.transcribe(audio_path, language='pt')

            # Save transcript
            transcript_path = TEMP_TRANSCRIPTS_DIR / f"{result.video_id}_transcript.txt"
            write_file(transcript_path, result.transcript)

            # Update video state
            video['transcript_path'] = str(transcript_path)
            video['status'] = 'transcribed'
            video['costs']['transcription'] = result.cost
            total_cost += result.cost

            logger.info(f"Transcribed: {transcript_path} (${result.cost:.4f})")

        except Exception as e:
            logger.error(f"Transcription failed for {video.get('video_id')}: {e}")
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
