#!/usr/bin/env python3
"""
WhatsApp message generation for GDG Londrina events and newsletters.

Supports 4 message types:
- event_announcement: Initial event announcement
- speaker_spotlight: Individual speaker/talk promotion
- reminder: Last-chance urgency message before event
- newsletter_promo: Post-event newsletter promotion
"""

import os
import sys
import json
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env
load_dotenv()

from tools.ai_client import AIClient
from tools.file_utils import read_json, read_file, write_file, ensure_directory

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "whatsapp"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"


class WhatsAppMessageType(Enum):
    """Supported WhatsApp message types."""
    EVENT_ANNOUNCEMENT = "event_announcement"
    SPEAKER_SPOTLIGHT = "speaker_spotlight"
    REMINDER = "reminder"
    NEWSLETTER_PROMO = "newsletter_promo"
    ALL_PRE_EVENT = "all_pre_event"


# Mapping of message types to their prompt files
WHATSAPP_CONFIG = {
    WhatsAppMessageType.EVENT_ANNOUNCEMENT: {
        "prompt": "whatsapp_event_announcement_prompt.md",
        "output_suffix": "event_announcement",
    },
    WhatsAppMessageType.SPEAKER_SPOTLIGHT: {
        "prompt": "whatsapp_speaker_spotlight_prompt.md",
        "output_suffix": "speaker",
    },
    WhatsAppMessageType.REMINDER: {
        "prompt": "whatsapp_reminder_prompt.md",
        "output_suffix": "reminder",
    },
    WhatsAppMessageType.NEWSLETTER_PROMO: {
        "prompt": "whatsapp_newsletter_promo_prompt.md",
        "output_suffix": "newsletter_promo",
    },
}


def load_prompt(message_type: WhatsAppMessageType) -> str:
    """Load prompt file for a specific message type."""
    config = WHATSAPP_CONFIG[message_type]
    prompt_path = KNOWLEDGE_DIR / "prompts" / config["prompt"]

    try:
        return read_file(prompt_path)
    except FileNotFoundError:
        logger.error(f"Prompt not found: {prompt_path}")
        raise


def load_examples(message_type: WhatsAppMessageType) -> str:
    """Load relevant example files for context."""
    examples_dir = KNOWLEDGE_DIR / "examples"
    examples = []

    # Map message types to example files
    example_files = {
        WhatsAppMessageType.EVENT_ANNOUNCEMENT: ["whatsapp-announcement.md"],
        WhatsAppMessageType.SPEAKER_SPOTLIGHT: ["whatsapp-speaker-announcement.md"],
        WhatsAppMessageType.REMINDER: ["whatsapp-reminder-announcement.md"],
        WhatsAppMessageType.NEWSLETTER_PROMO: ["whatsapp-announcement.md"],  # Use general examples
    }

    for filename in example_files.get(message_type, []):
        example_path = examples_dir / filename
        if example_path.exists():
            try:
                content = read_file(example_path)
                examples.append(f"### {filename}\n\n{content}")
            except Exception as e:
                logger.warning(f"Could not load example {filename}: {e}")

    return "\n\n---\n\n".join(examples) if examples else ""


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-')


def generate_message(
    message_type: WhatsAppMessageType,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a WhatsApp message of the specified type.

    Args:
        message_type: Type of message to generate
        data: Input data for message generation

    Returns:
        Dict with output path, message content, and metadata
    """
    prompt_content = load_prompt(message_type)
    examples = load_examples(message_type)

    # Build system prompt
    system_prompt = f"""{prompt_content}

## Exemplos Reais de Referencia

{examples}
"""

    # Build user prompt based on message type
    user_prompt = _build_user_prompt(message_type, data)

    # Initialize AI client
    whatsapp_model = os.getenv('WHATSAPP_MODEL') or os.getenv('AI_MODEL')
    client = AIClient(model=whatsapp_model)

    try:
        logger.info(f"Generating {message_type.value} message...")

        result = client.generate(
            prompt=user_prompt,
            system=system_prompt
        )

        # Determine output filename
        output_path = _get_output_path(message_type, data)

        # Save message
        write_file(output_path, result.text)

        logger.info(
            f"Message generated: {output_path} "
            f"({result.input_tokens} in / {result.output_tokens} out, ${result.cost:.4f})"
        )

        return {
            "status": "completed",
            "output_path": str(output_path),
            "message_type": message_type.value,
            "cost": result.cost,
            "tokens": {
                "input": result.input_tokens,
                "output": result.output_tokens
            }
        }

    except Exception as e:
        logger.error(f"Message generation failed: {e}")
        return {
            "status": "failed",
            "message_type": message_type.value,
            "error": str(e)
        }


def _build_user_prompt(message_type: WhatsAppMessageType, data: Dict[str, Any]) -> str:
    """Build the user prompt based on message type and data."""

    if message_type == WhatsAppMessageType.EVENT_ANNOUNCEMENT:
        palestras_text = ""
        for p in data.get("palestras", []):
            palestras_text += f"""
- **Titulo**: {p.get('titulo', '')}
- **Palestrante**: {p.get('palestrante', '')}
- **Descricao**: {p.get('descricao', '')}
"""
        return f"""Gere uma mensagem de anuncio de evento com os seguintes dados:

## Dados do Evento

- **Titulo**: {data.get('titulo', '')}
- **Data**: {data.get('data', '')}
- **Horario**: {data.get('horario', '')}
- **Local**: {data.get('local', '')}
- **Link de Inscricao**: {data.get('link_inscricao', '')}

## Palestras

{palestras_text}

Gere as 2 alternativas conforme especificado no prompt."""

    elif message_type == WhatsAppMessageType.SPEAKER_SPOTLIGHT:
        palestrante = data.get("palestrante", {})
        credenciais = palestrante.get("credenciais", [])
        credenciais_text = "\n".join([f"- {c}" for c in credenciais])

        return f"""Gere uma mensagem de spotlight do palestrante com os seguintes dados:

## Dados do Evento

- **Titulo**: {data.get('titulo', '')}
- **Data**: {data.get('data', '')}
- **Horario**: {data.get('horario', '')}
- **Local**: {data.get('local', '')}
- **Link de Inscricao**: {data.get('link_inscricao', '')}

## Dados do Palestrante

- **Nome**: {palestrante.get('nome', '')}
- **Titulo da Palestra**: {palestrante.get('titulo_palestra', '')}
- **Descricao**: {palestrante.get('descricao', '')}
- **Bio**: {palestrante.get('bio', '')}
- **LinkedIn**: {palestrante.get('linkedin', '')}

### Credenciais

{credenciais_text}

Gere as 2 alternativas conforme especificado no prompt."""

    elif message_type == WhatsAppMessageType.REMINDER:
        palestras_text = ""
        for p in data.get("palestras", []):
            palestras_text += f"""
- **Titulo**: {p.get('titulo', '')}
- **Palestrante**: {p.get('palestrante', '')}
"""
        return f"""Gere uma mensagem de lembrete de evento com os seguintes dados:

## Dados do Evento

- **Titulo**: {data.get('titulo', '')}
- **Data**: {data.get('data', '')}
- **Horario**: {data.get('horario', '')}
- **Local**: {data.get('local', '')}
- **Link de Inscricao**: {data.get('link_inscricao', '')}
- **Urgencia**: {data.get('urgencia', 'Em breve')}

## Palestras

{palestras_text}

Gere as 2 alternativas conforme especificado no prompt."""

    elif message_type == WhatsAppMessageType.NEWSLETTER_PROMO:
        return f"""Gere uma mensagem de promocao da newsletter com os seguintes dados:

## Dados da Newsletter

- **Titulo**: {data.get('titulo', '')}
- **Subtitulo**: {data.get('subtitulo', '')}
- **Link**: {data.get('link', '')}
- **Palestrante**: {data.get('palestrante', '')}
- **Insight Principal**: {data.get('insight_principal', '')}
- **Tema**: {data.get('tema', '')}

Gere as 2 alternativas conforme especificado no prompt."""

    else:
        raise ValueError(f"Unknown message type: {message_type}")


def _get_output_path(message_type: WhatsAppMessageType, data: Dict[str, Any]) -> Path:
    """Generate output file path based on message type and data."""
    ensure_directory(OUTPUT_DIR)

    date_str = datetime.now().strftime("%Y-%m")
    config = WHATSAPP_CONFIG[message_type]
    suffix = config["output_suffix"]

    if message_type == WhatsAppMessageType.SPEAKER_SPOTLIGHT:
        # Include speaker name in filename
        palestrante = data.get("palestrante", {})
        speaker_name = palestrante.get("nome", "speaker")
        slug = slugify(speaker_name)
        filename = f"{date_str}-{suffix}_{slug}.md"
    else:
        filename = f"{date_str}-{suffix}.md"

    return OUTPUT_DIR / filename


def generate_all_pre_event(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate all pre-event messages at once.

    Args:
        data: Event data with speakers

    Returns:
        List of results for each generated message
    """
    results = []

    # 1. Event Announcement
    result = generate_message(WhatsAppMessageType.EVENT_ANNOUNCEMENT, data)
    results.append(result)

    # 2. Speaker Spotlights (one per speaker)
    for palestra in data.get("palestras", []):
        speaker_data = {
            "titulo": data.get("titulo"),
            "data": data.get("data"),
            "horario": data.get("horario"),
            "local": data.get("local"),
            "link_inscricao": data.get("link_inscricao"),
            "palestrante": {
                "nome": palestra.get("palestrante"),
                "titulo_palestra": palestra.get("titulo"),
                "descricao": palestra.get("descricao"),
                "bio": palestra.get("bio", ""),
                "credenciais": palestra.get("credenciais", []),
                "linkedin": palestra.get("linkedin", "")
            }
        }
        result = generate_message(WhatsAppMessageType.SPEAKER_SPOTLIGHT, speaker_data)
        results.append(result)

    # 3. Reminder
    result = generate_message(WhatsAppMessageType.REMINDER, data)
    results.append(result)

    return results


def main():
    """Main entry point for WhatsApp message generation."""
    parser = argparse.ArgumentParser(
        description="Generate WhatsApp messages for GDG Londrina events"
    )
    parser.add_argument(
        "--type", "-t",
        choices=[t.value for t in WhatsAppMessageType],
        required=True,
        help="Message type to generate"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to JSON input file with event/newsletter data"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Custom output path (optional)"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load input data
    try:
        data = read_json(args.input)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid JSON: {e}")
        sys.exit(1)

    message_type = WhatsAppMessageType(args.type)

    # Generate message(s)
    if message_type == WhatsAppMessageType.ALL_PRE_EVENT:
        results = generate_all_pre_event(data)
        total_cost = sum(r.get("cost", 0) for r in results)

        print(f"\nGenerated {len(results)} WhatsApp messages:")
        for r in results:
            status = "OK" if r["status"] == "completed" else "FAILED"
            print(f"  [{status}] {r.get('message_type')}: {r.get('output_path', r.get('error'))}")

        print(f"\nTotal cost: ${total_cost:.4f}")

        # Check for failures
        if any(r["status"] == "failed" for r in results):
            sys.exit(1)
    else:
        result = generate_message(message_type, data)

        # Handle custom output path
        if args.output and result.get("status") == "completed":
            import shutil
            shutil.copy(result["output_path"], args.output)
            result["output_path"] = args.output

        # Print summary
        if result.get("status") == "completed":
            print(f"\nWhatsApp message generation complete!")
            print(f"  - Type: {result['message_type']}")
            print(f"  - Output: {result['output_path']}")
            print(f"  - Cost: ${result.get('cost', 0):.4f}")
        else:
            print(f"\nMessage generation failed: {result.get('error')}")
            sys.exit(1)

    return result


if __name__ == "__main__":
    main()
