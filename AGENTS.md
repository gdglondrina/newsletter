# GDG Newsletter Automation - Orchestrator

This document defines the AI agent roles, routing logic, and operational guidelines for the newsletter automation pipeline.

## Overview

The newsletter automation system processes YouTube videos from GDG events to generate monthly newsletters. It follows a linear pipeline with checkpoint-based state management.

## Configuration

### Environment Variables

All execution scripts automatically load environment variables from `.env` using the `python-dotenv` library:

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env before any os.getenv() calls
```

This pattern eliminates the need for manual `source .env` commands and makes scripts self-contained.

### .env Structure

```bash
# =============================================================================
# API KEYS
# =============================================================================
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# =============================================================================
# MODELS (per-stage configuration)
# =============================================================================

# Default model (used when stage-specific model not set)
# AI_MODEL=gpt-4o

# Transcription (Whisper)
TRANSCRIPT_MODEL=whisper-1

# Summary generation
SUMMARY_MODEL=gpt-5-mini-2025-08-07

# Newsletter generation
NEWSLETTER_MODEL=gemini-3-flash-preview

# WhatsApp message generation
WHATSAPP_MODEL=gpt-5-mini-2025-08-07
```

### Per-Stage Model Configuration

Each pipeline stage can use a different model optimized for its specific task:

| Stage | Environment Variable | Purpose | Typical Model |
|-------|---------------------|---------|---------------|
| Transcription | `TRANSCRIPT_MODEL` | Audio to text | `whisper-1` |
| Summary | `SUMMARY_MODEL` | Talk summaries | `gpt-5-mini`, `gemini-3-flash` |
| Newsletter | `NEWSLETTER_MODEL` | Full newsletter | `gemini-3-flash`, `gpt-4o` |
| WhatsApp | `WHATSAPP_MODEL` | WhatsApp messages | `gpt-5-mini` |

**Benefits:**
- **Cost optimization**: Use cheaper models for simpler tasks
- **Quality control**: Use better models for critical outputs
- **Flexibility**: Easy to experiment with different models per stage

### Auto-loading Pattern

All execution scripts follow this pattern:

```python
#!/usr/bin/env python3
from dotenv import load_dotenv

# Load .env at module import time
load_dotenv()

# Now all os.getenv() calls will have access to .env variables
model = os.getenv('SUMMARY_MODEL') or os.getenv('AI_MODEL')
```

**No manual environment sourcing required** - scripts are fully portable and self-configuring.

## Agent Roles

### Newsletter Orchestrator (Primary)

**Responsibility**: Coordinate the entire pipeline and make routing decisions.

**Capabilities**:
- Initialize processing sessions
- Route to specialized agents based on current state
- Handle errors and determine recovery strategies
- Track costs and generate final reports

**Decision Logic**:
```
IF no state exists OR force_restart:
    Initialize new session
    Route to → Audio Extraction Agent

IF state.current_step == "audio_extraction":
    Route to → Audio Extraction Agent

IF state.current_step == "transcription":
    Route to → Transcription Agent

IF state.current_step == "summary":
    Route to → Content Generation Agent (summary mode)

IF state.current_step == "newsletter":
    Route to → Content Generation Agent (newsletter mode)

IF state.status == "completed":
    Generate summary report
    Update processing history
```

### Audio Extraction Agent

**Responsibility**: Download audio from YouTube videos.

**Directive**: `directives/audio-extraction.md`
**Script**: `execution/extract_audio.py`
**Tool**: `tools/youtube_downloader.py`

**Outputs**:
- Audio files in `temp/audio/{video_id}.m4a`
- Updated state with video metadata

**Error Handling**:
- Invalid URL → Skip and log error
- Network failure → Retry with backoff
- Video unavailable → Skip and continue

### Transcription Agent

**Responsibility**: Convert audio to text using Whisper API.

**Directive**: `directives/transcription.md`
**Script**: `execution/transcribe_audio.py`
**Tool**: `tools/whisper_client.py`

**Outputs**:
- Transcripts in `temp/transcripts/{video_id}_transcript.txt`
- Cost tracking per video

**Error Handling**:
- Rate limit → Retry with exponential backoff
- File too large → Log error, skip
- API error → Retry up to 3 times

### Content Generation Agent

**Responsibility**: Generate summaries and newsletters using AI.

**Directive**: `directives/content-generation.md`
**Scripts**:
- `execution/generate_summaries.py` (summary mode)
- `execution/generate_newsletter.py` (newsletter mode)
**Tool**: `tools/ai_client.py`

**Modes**:

1. **Summary Mode**: Generate individual talk summaries
   - Input: Transcript files
   - Output: `temp/summaries/{video_id}_summary.md`
   - Prompt: `knowledge/prompts/summary_prompt.md`

2. **Newsletter Mode**: Generate newsletters of various types
   - See [Newsletter Types](#newsletter-types) section below

## Newsletter Types

The system supports multiple newsletter types, each with its own template and prompt:

| Type | Purpose | Input | Output |
|------|---------|-------|--------|
| `talk_summary` | Post-event newsletter summarizing talks | Video transcripts/summaries | `YYYY-MM-talk-summary.md` |
| `event_announcement` | Announce upcoming events with speakers | Event JSON | `YYYY-MM-evento.md` |
| `networking_edition` | Networking-focused event announcement | Event JSON | `YYYY-MM-networking-edition.md` |
| `networking_fast_talks` | Networking + Fast Talks announcement | Event JSON | `YYYY-MM-networking-fast-talks.md` |

### Newsletter Files Structure

**Templates** (`knowledge/newsletter_templates/`):
- `talk_summary_template.md` - Post-event talk summaries
- `event_announcement_template.md` - Event announcements
- `networking_edition_template.md` - Networking events
- `networking_fast_talks_template.md` - Networking + Fast Talks

**Prompts** (`knowledge/prompts/`):
- `talk_summary_prompt.md` - Instructions for talk summaries
- `event_announcement_prompt.md` - Instructions for event announcements
- `networking_edition_prompt.md` - Instructions for networking editions
- `networking_fast_talks_prompt.md` - Instructions for fast talks editions

**Example Inputs** (`knowledge/examples/`):
- `event_announcement_input.json`
- `networking_edition_input.json`
- `networking_fast_talks_input.json`

### Newsletter Generation Usage

```bash
# Post-event talk summary (legacy, uses current_processing.json)
python execution/generate_newsletter.py

# Or with explicit type
python execution/generate_newsletter.py --type talk_summary

# Event announcement
python execution/generate_newsletter.py \
  --type event_announcement \
  --input knowledge/examples/event_announcement_input.json

# Networking edition
python execution/generate_newsletter.py \
  --type networking_edition \
  --input knowledge/examples/networking_edition_input.json

# Networking + Fast Talks
python execution/generate_newsletter.py \
  --type networking_fast_talks \
  --input knowledge/examples/networking_fast_talks_input.json

# Custom output path
python execution/generate_newsletter.py \
  --type event_announcement \
  --input event.json \
  --output output/my-custom-newsletter.md
```

### Event Input JSON Schema

For `event_announcement` type:
```json
{
  "newsletter_type": "event_announcement",
  "event": {
    "titulo": "GDG Londrina Meetup",
    "data": "26 de junho (quinta-feira)",
    "horario": "A partir das 19h",
    "local": "Teatro Unifil",
    "link_inscricao": "https://sympla.com.br/..."
  },
  "palestrantes": [
    {
      "nome": "Speaker Name",
      "linkedin": "https://linkedin.com/in/...",
      "titulo_palestra": "Talk Title",
      "descricao_palestra": "Talk description",
      "bio": "Speaker bio"
    }
  ],
  "contexto": {
    "tema_geral": "Theme connecting all talks",
    "informacao_extra": "Coffee break, networking, etc."
  }
}
```

For `networking_edition` type:
```json
{
  "newsletter_type": "networking_edition",
  "event": {
    "titulo": "GDG Londrina Meetup: Networking Edition",
    "data": "16 de abril (quarta-feira)",
    "horario": "A partir das 19h",
    "local_nome": "Bar Name",
    "local_endereco": "Address",
    "local_link_mapa": "https://maps.google.com/...",
    "link_inscricao": "https://sympla.com.br/..."
  },
  "atividades_extras": ["Videogames", "Games"],
  "evento_anterior": {
    "titulo": "Previous Event",
    "descricao": "What happened",
    "palestras": [{"palestrante": "Name", "titulo": "Title", "linkedin": "..."}]
  },
  "contexto": {
    "edicao": "primeira edicao 2025",
    "spoiler": "Fun spoiler about the event"
  }
}
```

For `networking_fast_talks` type:
```json
{
  "newsletter_type": "networking_fast_talks",
  "event": {
    "titulo": "GDG Londrina Meetup: Networking Edition + Fast Talks",
    "data": "29 de julho (terca-feira)",
    "horario": "A partir das 19h",
    "local_nome": "Venue Name",
    "local_endereco": "Address",
    "local_link_mapa": "https://maps.google.com/...",
    "link_inscricao": "https://sympla.com.br/...",
    "mes": "julho"
  },
  "evento_anterior": {
    "mes": "junho",
    "descricao": "What happened last month",
    "palestras": [{"titulo": "Title", "palestrante": "Name", "linkedin": "..."}]
  },
  "contexto": {
    "spoiler_local": "Fun fact about the venue",
    "beneficios_adicionais": "Food, drinks, etc."
  }
}
```

## WhatsApp Message Generation

The system generates promotional WhatsApp messages for events and newsletters.

**Directive**: `directives/whatsapp-message-generation.md`
**Script**: `execution/generate_whatsapp.py`

### Message Types

| Type | Purpose | When to Use | Output |
|------|---------|-------------|--------|
| `event_announcement` | Initial event announcement | When event is first published | `YYYY-MM-event_announcement.md` |
| `speaker_spotlight` | Individual speaker promotion | 1-2 weeks before event (one per speaker) | `YYYY-MM-speaker_{name}.md` |
| `reminder` | Last-chance urgency message | 1-2 days before event | `YYYY-MM-reminder.md` |
| `newsletter_promo` | Post-event newsletter promotion | After newsletter is published | `YYYY-MM-newsletter_promo.md` |
| `all_pre_event` | Batch mode (announcement + spotlights + reminder) | Generate all pre-event messages at once | Multiple files |

### WhatsApp Prompts

**Prompts** (`knowledge/prompts/`):
- `whatsapp_event_announcement_prompt.md` - Event announcements
- `whatsapp_speaker_spotlight_prompt.md` - Speaker spotlights
- `whatsapp_reminder_prompt.md` - Event reminders
- `whatsapp_newsletter_promo_prompt.md` - Newsletter promotions

**Examples** (`knowledge/examples/`):
- `whatsapp-announcement.md`
- `whatsapp-speaker-announcement.md`
- `whatsapp-reminder-announcement.md`

### Output Format

Each generation produces **2 alternatives**:

```markdown
<!-- ALTERNATIVAS DE WHATSAPP -->

## Opcao 1 (Recomendada)
[message with approach A]

---

## Opcao 2
[message with different angle]

---
<!-- FIM DAS ALTERNATIVAS -->
```

### Usage

```bash
# Generate event announcement
python execution/generate_whatsapp.py \
  --type event_announcement \
  --input event_data.json

# Generate speaker spotlight
python execution/generate_whatsapp.py \
  --type speaker_spotlight \
  --input speaker_data.json

# Generate reminder
python execution/generate_whatsapp.py \
  --type reminder \
  --input event_data.json

# Generate newsletter promo
python execution/generate_whatsapp.py \
  --type newsletter_promo \
  --input newsletter_data.json

# Generate all pre-event messages at once
python execution/generate_whatsapp.py \
  --type all_pre_event \
  --input event_data.json
```

### Input JSON Schema

For event-related messages (`event_announcement`, `speaker_spotlight`, `reminder`):
```json
{
  "titulo": "GDG Londrina Meetup Fevereiro 2026",
  "data": "15/02 (sabado)",
  "horario": "9h",
  "local": "Unicesumar Londrina",
  "link_inscricao": "https://sympla.com.br/...",
  "urgencia": "AMANHA",
  "palestras": [
    {
      "titulo": "Talk title",
      "palestrante": "Speaker name",
      "descricao": "Brief description",
      "bio": "Speaker bio",
      "credenciais": ["Credential 1", "Credential 2"],
      "linkedin": "https://linkedin.com/in/..."
    }
  ]
}
```

For newsletter promotion (`newsletter_promo`):
```json
{
  "titulo": "Newsletter title",
  "subtitulo": "Newsletter subtitle",
  "link": "https://gdglondrina.substack.com/p/...",
  "palestrante": "Speaker name",
  "insight_principal": "Key insight from the talk",
  "tema": "Main theme"
}
```

## State Management

### State File Location
`context/current_processing.json`

### State Schema
```json
{
  "session_id": "2026-01-newsletter",
  "started_at": "2026-01-15T10:00:00",
  "status": "in_progress|completed|failed",
  "current_step": "audio_extraction|transcription|summary|newsletter",
  "video_urls": ["url1", "url2"],
  "videos": [
    {
      "url": "https://...",
      "video_id": "xxx",
      "title": "Talk Title",
      "duration": 3600,
      "audio_path": "temp/audio/xxx.m4a",
      "transcript_path": "temp/transcripts/xxx_transcript.txt",
      "summary_path": "temp/summaries/xxx_summary.md",
      "status": "audio_extracted|transcribed|summarized",
      "costs": {
        "transcription": 0.36,
        "summary": 0.15
      }
    }
  ],
  "total_cost": 0.51,
  "errors": []
}
```

### Resume Strategy

On restart:
1. Load `current_processing.json`
2. Check `status` - if "completed", start new session
3. Check `current_step` to determine entry point
4. Skip already-completed items within each step
5. Continue from last checkpoint

## Error Handling Strategies

### Transient Errors (Retry)
- Network timeouts
- Rate limits (429)
- Server errors (500, 502, 503)
- Temporary API issues

**Strategy**: Exponential backoff (1s, 2s, 4s), max 3 retries

### Fatal Errors (Stop)
- Invalid API keys
- Quota exceeded
- Invalid input URLs
- File system errors

**Strategy**: Log error, save state, exit with clear message

### Partial Failures (Continue)
- One video fails but others succeed
- Non-critical step fails

**Strategy**: Log error to state, continue with remaining items

## Cost Tracking

All API calls track costs:
- **Whisper**: $0.006/minute of audio
- **Claude**: $3/$15 per million tokens (input/output)
- **OpenAI GPT-4o**: $2.50/$10 per million tokens
- **Gemini**: $0.35/$1.05 per million tokens

Costs are accumulated in:
- Per-video `costs` object
- Session `total_cost`
- Historical records in `processing_history.json`

## Routing to Directives

The orchestrator routes to directives based on current step:

| Step | Directive | Description |
|------|-----------|-------------|
| audio_extraction | `audio-extraction.md` | Download audio |
| transcription | `transcription.md` | Transcribe audio |
| summary | `content-generation.md` | Generate summaries |
| newsletter | `content-generation.md` | Generate talk summary newsletter |

### Standalone Newsletter Generation

Event announcement newsletters (`event_announcement`, `networking_edition`, `networking_fast_talks`) do not require the full pipeline. They can be generated directly from event JSON data:

```
Event JSON → generate_newsletter.py → Newsletter Markdown
```

This is in contrast to talk summary newsletters which require the full pipeline:

```
YouTube URLs → Audio → Transcription → Summaries → Newsletter
```

## Quality Gates

Before proceeding to next step:

1. **After Audio Extraction**
   - At least 1 audio file must exist
   - Files must be valid (non-zero size)

2. **After Transcription**
   - At least 1 transcript must exist
   - Transcripts must have content

3. **After Summary**
   - All transcribed videos must have summaries

4. **After Newsletter**
   - Newsletter file must exist
   - File must have minimum length (500 chars)

## Usage

### Start Talk Summary Pipeline (Full Flow)
```bash
./execution/orchestrator.sh <url1> <url2>
```

### Resume After Failure
```bash
./execution/orchestrator.sh  # Resumes from saved state
```

### Force Restart
```bash
./execution/orchestrator.sh --force-restart <url1> <url2>
```

### Direct Python Execution
```bash
source gdg-venv/bin/activate
python execution/pipeline.py <url1> <url2>
```

### Generate Event Announcement Newsletter (No Pipeline)
```bash
source gdg-venv/bin/activate

# Create event JSON file with speaker info, dates, etc.
# See knowledge/examples/event_announcement_input.json for schema

python execution/generate_newsletter.py \
  --type event_announcement \
  --input my_event.json
```

### Generate Networking Edition Newsletter
```bash
source gdg-venv/bin/activate
python execution/generate_newsletter.py \
  --type networking_edition \
  --input my_networking_event.json
```

### Generate Networking + Fast Talks Newsletter
```bash
source gdg-venv/bin/activate
python execution/generate_newsletter.py \
  --type networking_fast_talks \
  --input my_fast_talks_event.json
```
