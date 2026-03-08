# GDG Newsletter Automation

Automate the generation of monthly GDG (Google Developer Group) newsletters from YouTube talk recordings.

## Overview

This pipeline processes YouTube videos of GDG talks and generates a formatted newsletter in markdown:

```
YouTube Videos → Audio → Transcript → Summaries → Newsletter
```

**Features:**
- Downloads audio from YouTube using yt-dlp
- Transcribes Portuguese audio using OpenAI Whisper API
- Generates summaries using configurable AI (Claude, OpenAI, or Gemini)
- Produces formatted newsletter in markdown
- Resume-from-failure support with state checkpointing
- Cost tracking for all API calls

## Quick Start

```bash
# 1. Clone and setup
cd gdg
cp .env.example .env
# Edit .env with your API keys

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
brew install yt-dlp  # if not installed

# 3. Run
./execution/orchestrator.sh \
  "https://www.youtube.com/watch?v=VIDEO1" \
  "https://www.youtube.com/watch?v=VIDEO2"

# Output: output/YYYY-MM-newsletter.md
```

## Requirements

- Python 3.9+
- macOS or Linux
- yt-dlp (`brew install yt-dlp`)
- API keys for:
  - OpenAI (required for Whisper transcription)
  - One of: Anthropic Claude, OpenAI GPT, or Google Gemini

## Configuration

### Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Required variables:

```bash
# Transcription (required)
OPENAI_API_KEY=sk-...

# AI Provider (choose one: 'claude', 'openai', 'gemini')
AI_PROVIDER=claude

# Provider-specific keys
ANTHROPIC_API_KEY=sk-ant-...  # For Claude
# OPENAI_API_KEY (already set above, also used for GPT)
GOOGLE_API_KEY=...  # For Gemini

# Optional
LOG_LEVEL=INFO
```

### AI Provider Comparison

| Provider | Model | Cost (2 talks) | Best For |
|----------|-------|----------------|----------|
| Claude | claude-sonnet-4-5 | ~$0.70 | Quality, nuanced writing |
| OpenAI | gpt-4o | ~$0.55 | Balanced performance |
| Gemini | gemini-1.5-pro | ~$0.30 | Cost-conscious, free tier |

## Usage

### Basic Usage

```bash
# Activate environment
source venv/bin/activate

# Run with 2 YouTube URLs
./execution/orchestrator.sh \
  "https://www.youtube.com/watch?v=xxx" \
  "https://www.youtube.com/watch?v=yyy"
```

### Resume After Failure

If the pipeline crashes, just run it again - it resumes from the last checkpoint:

```bash
./execution/orchestrator.sh
```

### Force Restart

To start fresh, ignoring previous state:

```bash
./execution/orchestrator.sh --force-restart \
  "https://www.youtube.com/watch?v=xxx" \
  "https://www.youtube.com/watch?v=yyy"
```

### Direct Python Execution

```bash
source venv/bin/activate
python execution/pipeline.py <url1> <url2>
```

## Project Structure

```
gdg/
├── AGENTS.md                    # Orchestrator logic and agent definitions
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
│
├── directives/                  # Workflow descriptions (markdown)
│   ├── newsletter-generation.md
│   ├── audio-extraction.md
│   ├── transcription.md
│   └── content-generation.md
│
├── execution/                   # Executable scripts
│   ├── orchestrator.sh          # Main entry point
│   ├── pipeline.py              # Python orchestrator
│   ├── extract_audio.py
│   ├── transcribe_audio.py
│   ├── generate_summaries.py
│   └── generate_newsletter.py
│
├── tools/                       # Reusable utilities
│   ├── youtube_downloader.py    # yt-dlp wrapper
│   ├── whisper_client.py        # Whisper API client
│   ├── ai_client.py             # Multi-provider AI client
│   ├── file_utils.py            # File operations
│   └── error_handler.py         # Retry logic
│
├── knowledge/                   # Templates and prompts
│   ├── newsletter_templates/
│   │   ├── template.md
│   │   ├── tone_guidelines.md
│   │   └── structure_requirements.md
│   └── prompts/
│       ├── summary_prompt.md
│       └── newsletter_prompt.md
│
├── context/                     # Runtime state (git-ignored)
│   ├── current_processing.json
│   └── processing_history.json
│
├── temp/                        # Temporary files (git-ignored)
│   ├── audio/
│   ├── transcripts/
│   └── summaries/
│
└── output/                      # Generated newsletters (git-ignored)
```

## Cost Estimation

For 2 one-hour talks:

| Step | Cost |
|------|------|
| Whisper transcription | $0.72 (2 × $0.36) |
| AI summaries | $0.30-0.70 |
| Newsletter generation | $0.20-0.40 |
| **Total** | **$1.20-1.80/month** |

Actual costs are tracked in `context/processing_history.json`.

## Customization

### Newsletter Template

Edit `knowledge/newsletter_templates/template.md` to change the newsletter structure.

### Tone and Style

Edit `knowledge/newsletter_templates/tone_guidelines.md` to adjust the writing style.

### AI Prompts

- `knowledge/prompts/summary_prompt.md` - How talks are summarized
- `knowledge/prompts/newsletter_prompt.md` - How the final newsletter is generated

## Troubleshooting

### "yt-dlp not installed"

```bash
brew install yt-dlp
# or
pip install yt-dlp
```

### "OPENAI_API_KEY not set"

Ensure your `.env` file exists and contains valid API keys.

### "File too large for Whisper"

Whisper API has a 25MB limit. For longer videos, the audio may exceed this. Consider:
- Using lower quality audio extraction
- Splitting audio (not yet implemented)

### Pipeline stuck or failing

Check state and logs:

```bash
# View current state
cat context/current_processing.json

# Reset and start fresh
./execution/orchestrator.sh --force-restart <urls>
```

### Rate limiting

The pipeline automatically retries with exponential backoff. If you hit persistent rate limits:
- Wait a few minutes and retry
- Check your API quota/billing

## Architecture

The system uses a three-layer architecture:

1. **AGENTS.md** - Orchestrator defining routing logic and agent roles
2. **directives/** - Declarative workflow descriptions (what to do)
3. **execution/** - Implementation scripts (how to do it)

This separation allows:
- Non-developers to modify workflows via markdown
- Easy addition of new steps or providers
- Clear debugging paths

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with real YouTube videos
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
