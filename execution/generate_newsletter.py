#!/usr/bin/env python3
"""
Newsletter generation supporting multiple types:
- talk_summary: Post-event newsletter summarizing talks (from video transcripts)
- event_announcement: Pre-event newsletter announcing upcoming events
- networking_edition: Networking-focused event announcement
- networking_fast_talks: Networking + Fast Talks event announcement
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.ai_client import AIClient
from tools.file_utils import read_json, write_json, read_file, write_file, ensure_directory

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CONTEXT_FILE = PROJECT_ROOT / "context" / "current_processing.json"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"


class NewsletterType(Enum):
    """Supported newsletter types."""
    TALK_SUMMARY = "talk_summary"
    EVENT_ANNOUNCEMENT = "event_announcement"
    NETWORKING_EDITION = "networking_edition"
    NETWORKING_FAST_TALKS = "networking_fast_talks"


# Mapping of newsletter types to their template and prompt files
NEWSLETTER_CONFIG = {
    NewsletterType.TALK_SUMMARY: {
        "template": "talk_summary_template.md",
        "prompt": "talk_summary_prompt.md",
    },
    NewsletterType.EVENT_ANNOUNCEMENT: {
        "template": "event_announcement_template.md",
        "prompt": "event_announcement_prompt.md",
    },
    NewsletterType.NETWORKING_EDITION: {
        "template": "networking_edition_template.md",
        "prompt": "networking_edition_prompt.md",
    },
    NewsletterType.NETWORKING_FAST_TALKS: {
        "template": "networking_fast_talks_template.md",
        "prompt": "networking_fast_talks_prompt.md",
    },
}


def load_knowledge_for_type(newsletter_type: NewsletterType) -> Dict[str, str]:
    """Load template and prompt files for a specific newsletter type."""
    config = NEWSLETTER_CONFIG[newsletter_type]
    knowledge = {}

    # Template
    template_path = KNOWLEDGE_DIR / "newsletter_templates" / config["template"]
    try:
        knowledge['template'] = read_file(template_path)
    except FileNotFoundError:
        logger.warning(f"Template not found: {template_path}")
        knowledge['template'] = ""

    # Prompt
    prompt_path = KNOWLEDGE_DIR / "prompts" / config["prompt"]
    try:
        knowledge['prompt'] = read_file(prompt_path)
    except FileNotFoundError:
        logger.warning(f"Prompt not found: {prompt_path}")
        knowledge['prompt'] = ""

    # Tone guidelines (shared across all types)
    tone_path = KNOWLEDGE_DIR / "newsletter_templates" / "tone_guidelines.md"
    try:
        knowledge['tone'] = read_file(tone_path)
    except FileNotFoundError:
        knowledge['tone'] = get_default_tone_guidelines()

    # Structure requirements (shared across all types)
    structure_path = KNOWLEDGE_DIR / "newsletter_templates" / "structure_requirements.md"
    try:
        knowledge['structure'] = read_file(structure_path)
    except FileNotFoundError:
        knowledge['structure'] = ""

    return knowledge


def get_default_tone_guidelines() -> str:
    """Default tone guidelines."""
    return """# Diretrizes de Tom e Estilo

## Voz da Newsletter

- **Profissional mas acessivel**: Tecnico sem ser intimidador
- **Entusiasmado mas nao exagerado**: Mostre paixao genuina pela tecnologia
- **Inclusivo**: Use linguagem que acolha desenvolvedores de todos os niveis
- **Conciso**: Respeite o tempo do leitor

## Portugues Brasileiro

- Use portugues brasileiro natural e contemporaneo
- Evite anglicismos desnecessarios, mas termos tecnicos em ingles sao aceitaveis
- Mantenha paragrafos curtos e escaneáveis
- Use bullet points para listas de conceitos
"""


def generate_talk_summary_newsletter(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a post-event newsletter from talk summaries.

    Args:
        state: Processing state with video summaries

    Returns:
        Updated state with newsletter path
    """
    knowledge = load_knowledge_for_type(NewsletterType.TALK_SUMMARY)

    # Collect summaries
    summaries = []
    for video in state.get('videos', []):
        summary_path = video.get('summary_path')
        if summary_path and Path(summary_path).exists():
            summary_content = read_file(summary_path)
            summaries.append({
                'title': video.get('title', 'Untitled'),
                'url': video.get('url', ''),
                'video_id': video.get('video_id', ''),
                'summary': summary_content
            })

    if not summaries:
        logger.error("No summaries found to generate newsletter")
        state['status'] = 'failed'
        state['error'] = "No summaries available"
        return state

    # Build the prompt
    system_prompt = f"""{knowledge['prompt']}

## Template de Referencia

{knowledge['template']}

## Diretrizes de Tom

{knowledge['tone']}
"""

    summaries_text = ""
    for i, s in enumerate(summaries, 1):
        summaries_text += f"""
### Palestra {i}: {s['title']}
**Link**: {s['url']}

{s['summary']}

---
"""

    user_prompt = f"""Por favor, gere a newsletter do mes de {datetime.now().strftime('%B %Y')} usando os seguintes resumos de palestras:

{summaries_text}

Gere a newsletter completa em Markdown, seguindo o template e as diretrizes de tom fornecidos."""

    return _generate_and_save(state, system_prompt, user_prompt, "talk-summary")


def generate_event_announcement_newsletter(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an event announcement newsletter.

    Args:
        event_data: Event details (speakers, date, location, etc.)

    Returns:
        State with newsletter path and cost
    """
    knowledge = load_knowledge_for_type(NewsletterType.EVENT_ANNOUNCEMENT)

    system_prompt = f"""{knowledge['prompt']}

## Template de Referencia

{knowledge['template']}

## Diretrizes de Tom

{knowledge['tone']}
"""

    # Format event data for the prompt
    event = event_data.get('event', {})
    palestrantes = event_data.get('palestrantes', [])
    contexto = event_data.get('contexto', {})

    palestrantes_text = ""
    for p in palestrantes:
        palestrantes_text += f"""
### Palestrante: {p.get('nome', '')}
- **LinkedIn**: {p.get('linkedin', '')}
- **Titulo da Palestra**: {p.get('titulo_palestra', '')}
- **Descricao**: {p.get('descricao_palestra', '')}
- **Bio**: {p.get('bio', '')}
"""

    user_prompt = f"""Por favor, gere uma newsletter de anuncio de evento para o GDG Londrina com os seguintes dados:

## Dados do Evento

- **Titulo**: {event.get('titulo', '')}
- **Data**: {event.get('data', '')}
- **Horario**: {event.get('horario', '')}
- **Local**: {event.get('local', '')}
- **Link de Inscricao**: {event.get('link_inscricao', '')}

## Palestrantes

{palestrantes_text}

## Contexto Adicional

- **Tema Geral**: {contexto.get('tema_geral', '')}
- **Informacao Extra**: {contexto.get('informacao_extra', '')}

Gere a newsletter completa em Markdown, seguindo o template e as diretrizes de tom fornecidos.
Use placeholders de imagem como [Foto do palestrante] onde apropriado."""

    state = {'newsletter_type': 'event_announcement'}
    return _generate_and_save(state, system_prompt, user_prompt, "evento")


def generate_networking_edition_newsletter(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a networking edition newsletter.

    Args:
        event_data: Event details

    Returns:
        State with newsletter path and cost
    """
    knowledge = load_knowledge_for_type(NewsletterType.NETWORKING_EDITION)

    system_prompt = f"""{knowledge['prompt']}

## Template de Referencia

{knowledge['template']}

## Diretrizes de Tom

{knowledge['tone']}
"""

    event = event_data.get('event', {})
    atividades = event_data.get('atividades_extras', [])
    evento_anterior = event_data.get('evento_anterior', {})
    contexto = event_data.get('contexto', {})

    atividades_text = "\n".join([f"- {a}" for a in atividades])

    evento_anterior_text = ""
    if evento_anterior:
        palestras = evento_anterior.get('palestras', [])
        palestras_text = ""
        for p in palestras:
            palestras_text += f"\n- [{p.get('palestrante', '')}]({p.get('linkedin', '')}) - \"{p.get('titulo', '')}\""
            if p.get('link_resumo'):
                palestras_text += f" ([resumo]({p.get('link_resumo')}))"
        evento_anterior_text = f"""
## Evento Anterior
- **Titulo**: {evento_anterior.get('titulo', '')}
- **Descricao**: {evento_anterior.get('descricao', '')}
- **Palestras**: {palestras_text}
"""

    user_prompt = f"""Por favor, gere uma newsletter de Networking Edition para o GDG Londrina com os seguintes dados:

## Dados do Evento

- **Titulo**: {event.get('titulo', '')}
- **Data**: {event.get('data', '')}
- **Horario**: {event.get('horario', '')}
- **Local**: {event.get('local_nome', '')} | {event.get('local_endereco', '')}
- **Link do Mapa**: {event.get('local_link_mapa', '')}
- **Link de Inscricao**: {event.get('link_inscricao', '')}

## Atividades Extras

{atividades_text}

{evento_anterior_text}

## Contexto

- **Edicao**: {contexto.get('edicao', '')}
- **Spoiler**: {contexto.get('spoiler', '')}

Gere a newsletter completa em Markdown, seguindo o template e as diretrizes de tom fornecidos."""

    state = {'newsletter_type': 'networking_edition'}
    return _generate_and_save(state, system_prompt, user_prompt, "networking-edition")


def generate_networking_fast_talks_newsletter(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a networking + fast talks edition newsletter.

    Args:
        event_data: Event details

    Returns:
        State with newsletter path and cost
    """
    knowledge = load_knowledge_for_type(NewsletterType.NETWORKING_FAST_TALKS)

    system_prompt = f"""{knowledge['prompt']}

## Template de Referencia

{knowledge['template']}

## Diretrizes de Tom

{knowledge['tone']}
"""

    event = event_data.get('event', {})
    evento_anterior = event_data.get('evento_anterior', {})
    contexto = event_data.get('contexto', {})

    evento_anterior_text = ""
    if evento_anterior:
        palestras = evento_anterior.get('palestras', [])
        palestras_text = ""
        for p in palestras:
            palestras_text += f"\n- \"{p.get('titulo', '')}\" com [{p.get('palestrante', '')}]({p.get('linkedin', '')})"
            if p.get('link_resumo'):
                palestras_text += f" ([resumo]({p.get('link_resumo')}))"
        evento_anterior_text = f"""
## Evento Anterior (mes: {evento_anterior.get('mes', '')})
- **Descricao**: {evento_anterior.get('descricao', '')}
- **Palestras**: {palestras_text}
"""

    user_prompt = f"""Por favor, gere uma newsletter de Networking Edition + Fast Talks para o GDG Londrina com os seguintes dados:

## Dados do Evento

- **Titulo**: {event.get('titulo', '')}
- **Data**: {event.get('data', '')}
- **Horario**: {event.get('horario', '')}
- **Local**: {event.get('local_nome', '')} | {event.get('local_endereco', '')}
- **Link do Mapa**: {event.get('local_link_mapa', '')}
- **Link de Inscricao**: {event.get('link_inscricao', '')}
- **Mes**: {event.get('mes', '')}

{evento_anterior_text}

## Contexto

- **Spoiler sobre o Local**: {contexto.get('spoiler_local', '')}
- **Beneficios Adicionais**: {contexto.get('beneficios_adicionais', '')}

Gere a newsletter completa em Markdown, seguindo o template e as diretrizes de tom fornecidos.
IMPORTANTE: Lembre-se de incluir a observacao sobre o ingresso Fast Talk pelo menos 3 vezes no texto."""

    state = {'newsletter_type': 'networking_fast_talks'}
    return _generate_and_save(state, system_prompt, user_prompt, "networking-fast-talks")


def _generate_and_save(
    state: Dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    output_suffix: str
) -> Dict[str, Any]:
    """
    Common generation and saving logic.

    Args:
        state: Current state to update
        system_prompt: System prompt for AI
        user_prompt: User prompt for AI
        output_suffix: Suffix for output filename

    Returns:
        Updated state with newsletter path
    """
    ensure_directory(OUTPUT_DIR)

    # Initialize AI client with per-stage model configuration
    newsletter_model = os.getenv('NEWSLETTER_MODEL')
    client = AIClient(model=newsletter_model)

    try:
        logger.info(f"Generating {output_suffix} newsletter...")

        result = client.generate(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=10000
        )

        # Generate output filename
        date_str = datetime.now().strftime("%Y-%m")
        output_path = OUTPUT_DIR / f"{date_str}-{output_suffix}.md"

        # Save newsletter
        write_file(output_path, result.text)

        # Update state
        state['newsletter_path'] = str(output_path)
        state['status'] = 'completed'
        state['costs'] = state.get('costs', {})
        state['costs']['newsletter'] = result.cost
        state['total_cost'] = state.get('total_cost', 0) + result.cost

        logger.info(
            f"Newsletter generated: {output_path} "
            f"({result.input_tokens} in / {result.output_tokens} out, ${result.cost:.4f})"
        )

    except Exception as e:
        logger.error(f"Newsletter generation failed: {e}")
        state['status'] = 'failed'
        state['error'] = str(e)

    return state


def generate_newsletter(
    newsletter_type: NewsletterType,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main dispatcher for newsletter generation.

    Args:
        newsletter_type: Type of newsletter to generate
        data: Input data (varies by type)

    Returns:
        State with newsletter path and metadata
    """
    generators = {
        NewsletterType.TALK_SUMMARY: generate_talk_summary_newsletter,
        NewsletterType.EVENT_ANNOUNCEMENT: generate_event_announcement_newsletter,
        NewsletterType.NETWORKING_EDITION: generate_networking_edition_newsletter,
        NewsletterType.NETWORKING_FAST_TALKS: generate_networking_fast_talks_newsletter,
    }

    generator = generators.get(newsletter_type)
    if not generator:
        raise ValueError(f"Unknown newsletter type: {newsletter_type}")

    return generator(data)


def main():
    """
    Main entry point for newsletter generation.

    Supports two modes:
    1. Legacy mode: No arguments, uses current_processing.json for talk summaries
    2. New mode: --type and --input arguments for any newsletter type
    """
    parser = argparse.ArgumentParser(
        description="Generate GDG newsletters of various types"
    )
    parser.add_argument(
        "--type", "-t",
        choices=[t.value for t in NewsletterType],
        default=NewsletterType.TALK_SUMMARY.value,
        help="Newsletter type to generate"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Path to JSON input file with event data (required for non-talk-summary types)"
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

    newsletter_type = NewsletterType(args.type)

    # Load input data
    if newsletter_type == NewsletterType.TALK_SUMMARY:
        # Legacy behavior: load from processing state
        if args.input:
            data = read_json(args.input)
        else:
            try:
                data = read_json(CONTEXT_FILE)
            except FileNotFoundError:
                print("Error: No processing state found. Run previous steps first or provide --input.")
                sys.exit(1)
    else:
        # New types require explicit input file
        if not args.input:
            print(f"Error: --input is required for newsletter type '{args.type}'")
            print(f"Example: python generate_newsletter.py --type {args.type} --input event_data.json")
            sys.exit(1)
        data = read_json(args.input)

    # Generate newsletter
    state = generate_newsletter(newsletter_type, data)

    # Handle custom output path
    if args.output and state.get('status') == 'completed':
        import shutil
        shutil.copy(state['newsletter_path'], args.output)
        state['newsletter_path'] = args.output

    # Save state for talk_summary type (legacy behavior)
    if newsletter_type == NewsletterType.TALK_SUMMARY:
        write_json(CONTEXT_FILE, state)

    # Print summary
    if state.get('status') == 'completed':
        print(f"\nNewsletter generation complete!")
        print(f"  - Type: {newsletter_type.value}")
        print(f"  - Output: {state['newsletter_path']}")
        print(f"  - Cost: ${state.get('total_cost', 0):.4f}")
    else:
        print(f"\nNewsletter generation failed: {state.get('error')}")
        sys.exit(1)

    return state


if __name__ == "__main__":
    main()
