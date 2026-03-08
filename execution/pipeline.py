#!/usr/bin/env python3
"""
Main pipeline orchestrator for the newsletter automation.

Coordinates all steps: extract → transcribe → summarize → generate newsletter
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from tools.file_utils import read_json, write_json, ensure_directory
from tools.error_handler import FatalError

# Import execution steps
from execution import extract_audio, transcribe_audio, generate_summaries, generate_newsletter

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONTEXT_DIR = PROJECT_ROOT / "context"
CONTEXT_FILE = CONTEXT_DIR / "current_processing.json"
HISTORY_FILE = CONTEXT_DIR / "processing_history.json"


def initialize_state(video_urls: List[str], force_restart: bool = False) -> Dict[str, Any]:
    """
    Initialize or load processing state.

    Args:
        video_urls: List of YouTube URLs to process
        force_restart: If True, ignore existing state and start fresh

    Returns:
        Processing state dict
    """
    ensure_directory(CONTEXT_DIR)

    # Check for existing state
    if not force_restart and CONTEXT_FILE.exists():
        try:
            state = read_json(CONTEXT_FILE)
            if state.get('status') != 'completed':
                logger.info(f"Resuming from step: {state.get('current_step')}")
                return state
        except Exception as e:
            logger.warning(f"Could not load existing state: {e}")

    # Create new state
    session_id = datetime.now().strftime("%Y-%m-newsletter")
    state = {
        'session_id': session_id,
        'started_at': datetime.now().isoformat(),
        'status': 'in_progress',
        'current_step': 'audio_extraction',
        'video_urls': video_urls,
        'videos': [],
        'total_cost': 0.0,
        'errors': []
    }

    write_json(CONTEXT_FILE, state)
    logger.info(f"Started new session: {session_id}")

    return state


def save_state(state: Dict[str, Any]) -> None:
    """Save current state to file."""
    write_json(CONTEXT_FILE, state)


def update_history(state: Dict[str, Any]) -> None:
    """Add completed session to processing history."""
    try:
        history = read_json(HISTORY_FILE)
    except FileNotFoundError:
        history = {'sessions': []}

    # Add session summary
    session_summary = {
        'session_id': state.get('session_id'),
        'started_at': state.get('started_at'),
        'completed_at': datetime.now().isoformat(),
        'status': state.get('status'),
        'videos_processed': len(state.get('videos', [])),
        'total_cost': state.get('total_cost', 0),
        'newsletter_path': state.get('newsletter_path'),
        'errors': len(state.get('errors', []))
    }

    history['sessions'].append(session_summary)
    write_json(HISTORY_FILE, history)


def print_summary(state: Dict[str, Any]) -> None:
    """Print final processing summary."""
    print("\n" + "=" * 50)
    print("NEWSLETTER GENERATION COMPLETE")
    print("=" * 50)

    print(f"\nSession: {state.get('session_id')}")
    print(f"Status: {state.get('status')}")

    print(f"\nVideos processed: {len(state.get('videos', []))}")
    for video in state.get('videos', []):
        status_icon = "✓" if video.get('status') == 'summarized' else "✗"
        print(f"  {status_icon} {video.get('title', 'Unknown')}")

    if state.get('errors'):
        print(f"\nErrors: {len(state['errors'])}")
        for error in state['errors']:
            print(f"  - {error.get('url', 'Unknown')}: {error.get('error', 'Unknown error')}")

    print(f"\nCost breakdown:")
    total = 0
    for video in state.get('videos', []):
        costs = video.get('costs', {})
        video_cost = sum(costs.values())
        total += video_cost
        print(f"  - {video.get('video_id', 'Unknown')}: ${video_cost:.4f}")
        for step, cost in costs.items():
            print(f"      {step}: ${cost:.4f}")

    if state.get('costs', {}).get('newsletter'):
        nl_cost = state['costs']['newsletter']
        total += nl_cost
        print(f"  - Newsletter: ${nl_cost:.4f}")

    print(f"\nTotal cost: ${total:.4f}")

    if state.get('newsletter_path'):
        print(f"\nOutput: {state['newsletter_path']}")

    print("\n" + "=" * 50)


def run_pipeline(video_urls: List[str], force_restart: bool = False) -> Dict[str, Any]:
    """
    Run the complete newsletter generation pipeline.

    Args:
        video_urls: List of YouTube video URLs
        force_restart: If True, start fresh ignoring existing state

    Returns:
        Final processing state
    """
    # Validate inputs
    if not video_urls:
        raise FatalError("No video URLs provided")

    # Initialize state
    state = initialize_state(video_urls, force_restart)

    try:
        # Step 1: Audio Extraction
        if state['current_step'] in ['audio_extraction', 'pending']:
            logger.info("Step 1/4: Extracting audio...")
            state = extract_audio.extract_audio(state.get('video_urls', video_urls), state)
            state['current_step'] = 'transcription'
            save_state(state)

        # Step 2: Transcription
        if state['current_step'] == 'transcription':
            logger.info("Step 2/4: Transcribing audio...")
            state = transcribe_audio.transcribe_audio(state)
            state['current_step'] = 'summary'
            save_state(state)

        # Step 3: Summary Generation
        if state['current_step'] == 'summary':
            logger.info("Step 3/4: Generating summaries...")
            state = generate_summaries.generate_summaries(state)
            state['current_step'] = 'newsletter'
            save_state(state)

        # Step 4: Newsletter Generation
        if state['current_step'] == 'newsletter':
            logger.info("Step 4/4: Generating newsletter...")
            state = generate_newsletter.generate_newsletter(state)
            save_state(state)

        # Finalize
        if state['status'] == 'completed':
            state['completed_at'] = datetime.now().isoformat()
            save_state(state)
            update_history(state)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        state['status'] = 'failed'
        state['error'] = str(e)
        save_state(state)
        raise

    return state


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='GDG Newsletter Automation Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline.py https://youtube.com/watch?v=xxx https://youtube.com/watch?v=yyy
  python pipeline.py --force-restart https://youtube.com/watch?v=xxx
        """
    )
    parser.add_argument(
        'urls',
        nargs='*',
        help='YouTube video URLs to process'
    )
    parser.add_argument(
        '--force-restart',
        action='store_true',
        help='Ignore existing state and start fresh'
    )
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'INFO'),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load environment
    load_dotenv()

    # Validate environment
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not set in .env file")
        sys.exit(1)

    provider = os.getenv('AI_PROVIDER', 'claude')
    if provider == 'claude' and not os.getenv('ANTHROPIC_API_KEY'):
        print("Error: ANTHROPIC_API_KEY not set (required for Claude provider)")
        sys.exit(1)
    elif provider == 'gemini' and not os.getenv('GOOGLE_API_KEY'):
        print("Error: GOOGLE_API_KEY not set (required for Gemini provider)")
        sys.exit(1)

    # Get URLs
    if not args.urls:
        # Check if resuming from existing state
        if CONTEXT_FILE.exists():
            try:
                state = read_json(CONTEXT_FILE)
                if state.get('status') != 'completed':
                    args.urls = state.get('video_urls', [])
                    print(f"Resuming with URLs from previous session...")
            except Exception:
                pass

    if not args.urls:
        parser.print_help()
        print("\nError: No URLs provided and no resumable session found")
        sys.exit(1)

    print(f"\nGDG Newsletter Automation")
    print(f"Provider: {provider}")
    print(f"Videos: {len(args.urls)}")
    print()

    try:
        state = run_pipeline(args.urls, args.force_restart)
        print_summary(state)

        if state['status'] == 'completed':
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted. State saved. Run again to resume.")
        sys.exit(130)
    except Exception as e:
        logger.exception("Pipeline failed")
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
