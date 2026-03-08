#!/usr/bin/env python3
"""
Summary generation step: Generate talk summaries using AI.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.ai_client import AIClient
from tools.file_utils import read_json, write_json, read_file, write_file, ensure_directory

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMP_SUMMARIES_DIR = PROJECT_ROOT / "temp" / "summaries"
CONTEXT_FILE = PROJECT_ROOT / "context" / "current_processing.json"
SUMMARY_PROMPT_PATH = PROJECT_ROOT / "knowledge" / "prompts" / "summary_prompt.md"


def load_summary_prompt() -> str:
    """Load the summary prompt from knowledge base."""
    try:
        return read_file(SUMMARY_PROMPT_PATH)
    except FileNotFoundError:
        # Default prompt if file not found
        return """You are a technical content summarizer for a Google Developer Group newsletter.

Analyze the following talk transcript and create a comprehensive summary in Portuguese (Brazilian).

Your summary should include:
1. **Título da Palestra**: The talk title
2. **Palestrante**: Speaker name (if mentioned)
3. **Resumo Executivo**: 2-3 sentence overview
4. **Principais Pontos**: 3-5 key takeaways as bullet points
5. **Conceitos Técnicos**: Technical concepts explained
6. **Aplicações Práticas**: How developers can apply this
7. **Citações Destacadas**: 1-2 notable quotes (if any)

Write in a professional but accessible tone. Keep technical accuracy while being understandable to developers of varying experience levels.

Format the output as clean markdown."""


def generate_summaries(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate summaries for transcribed talks.

    Args:
        state: Current processing state with transcripts

    Returns:
        Updated state with summary paths
    """
    ensure_directory(TEMP_SUMMARIES_DIR)

    # Initialize AI client with per-stage model configuration
    summary_model = os.getenv('SUMMARY_MODEL')
    client = AIClient(model=summary_model)
    system_prompt = load_summary_prompt()

    total_cost = state.get('total_cost', 0.0)

    for video in state.get('videos', []):
        # Check if already summarized
        if video.get('summary_path') and Path(video['summary_path']).exists():
            logger.info(f"Skipping already summarized: {video['video_id']}")
            continue

        transcript_path = video.get('transcript_path')
        if not transcript_path or not Path(transcript_path).exists():
            logger.error(f"Transcript not found for {video.get('video_id')}")
            continue

        try:
            logger.info(f"Generating summary for: {video['title']}")

            # Load transcript
            transcript = read_file(transcript_path)

            # Build prompt
            user_prompt = f"""Transcrição da palestra: "{video['title']}"

---

{transcript}

---

Por favor, gere um resumo estruturado desta palestra seguindo as diretrizes do sistema."""

            # Generate summary
            result = client.generate(
                prompt=user_prompt,
                system=system_prompt,
                max_tokens=4096
            )

            # Save summary
            summary_path = TEMP_SUMMARIES_DIR / f"{video['video_id']}_summary.md"
            write_file(summary_path, result.text)

            # Update video state
            video['summary_path'] = str(summary_path)
            video['status'] = 'summarized'
            video['costs']['summary'] = result.cost
            total_cost += result.cost

            logger.info(
                f"Generated summary: {summary_path} "
                f"({result.input_tokens} in / {result.output_tokens} out, ${result.cost:.4f})"
            )

        except Exception as e:
            logger.error(f"Summary generation failed for {video.get('video_id')}: {e}")
            video['status'] = 'summary_failed'
            video['error'] = str(e)

    # Update state
    state['total_cost'] = total_cost
    state['current_step'] = 'newsletter'

    return state


def main(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for summary generation.

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
            print("Error: No processing state found. Run previous steps first.")
            sys.exit(1)

    # Run summary generation
    state = generate_summaries(state)

    # Save state
    write_json(CONTEXT_FILE, state)

    # Print summary
    summarized = sum(1 for v in state['videos'] if v.get('status') == 'summarized')
    print(f"\nSummary generation complete:")
    print(f"  - {summarized}/{len(state['videos'])} talks summarized")
    print(f"  - Total cost so far: ${state['total_cost']:.4f}")

    return state


if __name__ == "__main__":
    main()
