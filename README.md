# GDG Newsletter Automation

Automates GDG Londrina content generation from YouTube talks and event metadata.

## Overview

The main pipeline processes YouTube videos and builds a talk-summary newsletter:

```text
YouTube Videos -> Audio -> Transcript -> Summaries -> Newsletter
```

The project also supports standalone generation for:
- Event announcement newsletters
- Networking editions
- Networking + Fast Talks editions
- WhatsApp promotional messages

## Features

- Audio download with `yt-dlp`
- Portuguese transcription via OpenAI Whisper API
- AI-based summary/newsletter generation (OpenAI, Claude, Gemini models)
- Checkpoint-based resume with `context/current_processing.json`
- Cost tracking per step and per session
- Standalone newsletter and WhatsApp generation modes

## Requirements

- Python 3.9+
- macOS or Linux
- `yt-dlp` installed (`brew install yt-dlp`)
- API keys:
  - `OPENAI_API_KEY` (required for transcription)
  - One or more generation providers as needed (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`)

## Quick Start (Full Talk Pipeline)

```bash
# 1) Setup
cp .env.example .env
# Edit .env with your keys

# 2) Dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install yt-dlp

# 3) Run
./execution/orchestrator.sh \
  "https://www.youtube.com/watch?v=VIDEO1" \
  "https://www.youtube.com/watch?v=VIDEO2"

# Output (talk summary): output/YYYY-MM-talk-summary.md
```

## Configuration

Create `.env` from template:

```bash
cp .env.example .env
```

Base variables:

```bash
# Required for Whisper transcription
OPENAI_API_KEY=sk-...

# Legacy pipeline provider selector (used by execution/pipeline.py checks)
AI_PROVIDER=claude

# Provider keys
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional
LOG_LEVEL=INFO
```

Optional per-stage model overrides:

```bash
TRANSCRIPT_MODEL=whisper-1
SUMMARY_MODEL=gpt-5-mini-2025-08-07
NEWSLETTER_MODEL=gemini-3-flash-preview
WHATSAPP_MODEL=gpt-5-mini-2025-08-07
AI_MODEL=gpt-4o
```

## Usage

### Full pipeline

```bash
source venv/bin/activate
./execution/orchestrator.sh "https://www.youtube.com/watch?v=xxx" "https://www.youtube.com/watch?v=yyy"
```

### Resume after failure

```bash
./execution/orchestrator.sh
```

### Force restart

```bash
./execution/orchestrator.sh --force-restart "https://www.youtube.com/watch?v=xxx" "https://www.youtube.com/watch?v=yyy"
```

### Direct Python execution

```bash
source venv/bin/activate
python execution/pipeline.py <url1> <url2>
```

### Standalone newsletter generation

```bash
# Talk summary (from current_processing.json)
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
```

### WhatsApp message generation

```bash
# One message type
python execution/generate_whatsapp.py \
  --type event_announcement \
  --input knowledge/examples/event_announcement_input.json

# Batch pre-event messages
python execution/generate_whatsapp.py \
  --type all_pre_event \
  --input knowledge/examples/event_announcement_input.json
```

Generated WhatsApp files are written to `output/whatsapp/`.

## Project Structure

```text
gdg/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── directives/
│   ├── audio-extraction.md
│   ├── transcription.md
│   ├── content-generation.md
│   ├── newsletter-generation.md
│   └── whatsapp-message-generation.md
├── execution/
│   ├── orchestrator.sh
│   ├── pipeline.py
│   ├── extract_audio.py
│   ├── transcribe_audio.py
│   ├── generate_summaries.py
│   ├── generate_newsletter.py
│   └── generate_whatsapp.py
├── tools/
│   ├── youtube_downloader.py
│   ├── whisper_client.py
│   ├── ai_client.py
│   ├── file_utils.py
│   └── error_handler.py
├── knowledge/
│   ├── newsletter_templates/
│   │   ├── talk_summary_template.md
│   │   ├── event_announcement_template.md
│   │   ├── networking_edition_template.md
│   │   ├── networking_fast_talks_template.md
│   │   ├── tone_guidelines.md
│   │   └── structure_requirements.md
│   ├── prompts/
│   │   ├── summary_prompt.md
│   │   ├── talk_summary_prompt.md
│   │   ├── event_announcement_prompt.md
│   │   ├── networking_edition_prompt.md
│   │   ├── networking_fast_talks_prompt.md
│   │   ├── whatsapp_event_announcement_prompt.md
│   │   ├── whatsapp_speaker_spotlight_prompt.md
│   │   ├── whatsapp_reminder_prompt.md
│   │   └── whatsapp_newsletter_promo_prompt.md
│   └── examples/
├── context/   (git-ignored runtime state)
├── temp/      (git-ignored intermediates)
└── output/    (git-ignored generated files)
```

## Cost Notes

Costs are tracked during execution and saved into processing state/history files.

Reference pricing constants in code:
- Whisper: `$0.006/min` (see `tools/whisper_client.py`)
- Claude / OpenAI / Gemini token pricing estimates (see `tools/ai_client.py`)

## Customization

- Templates: `knowledge/newsletter_templates/*.md`
- Prompts: `knowledge/prompts/*.md`
- Example inputs: `knowledge/examples/*.json`

## Troubleshooting

### `yt-dlp` not installed

```bash
brew install yt-dlp
```

### Missing API keys

Ensure `.env` exists and required keys are set for the model/provider you are using.

### Whisper file too large

Whisper API max file size is 25MB. If exceeded, reduce audio size or split audio before transcription.

### Pipeline stuck/failing

```bash
cat context/current_processing.json
./execution/orchestrator.sh --force-restart <urls>
```

### Rate limits

The project retries transient failures with exponential backoff. If persistent:
- wait and retry
- verify provider quota/billing

## Architecture

- `AGENTS.md`: routing + responsibilities
- `directives/`: operational workflows
- `execution/`: implementation scripts
- `tools/`: reusable clients/utilities
