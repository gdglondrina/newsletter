
 GDG Newsletter Automation - Implementation Plan

 Executive Summary

 Build an AI-powered newsletter automation pipeline for monthly GDG (Google Developer Group) events using the orchestrator/directives/execution architecture
 pattern. The system will process 2 YouTube videos (pt-br talks) per month and automatically generate a formatted newsletter in markdown.

 Tech Stack: yt-dlp (audio extraction) → OpenAI Whisper API (transcription) → Configurable AI Provider (Claude/OpenAI/Gemini for summary + newsletter
 generation) → Markdown output

 Estimated Monthly Cost: ~$2-3/month (2 talks × ~$0.36 Whisper + ~$0.50-1.50 AI generation, varies by provider)

 ---
 Architecture Overview

 Three-Layer Pattern

 AGENTS.md (Orchestrator)
     ↓ decision logic & routing
 /directives/ (Workflow Plans - markdown)
     ↓ execution instructions
 /execution/ (Implementation Scripts - python/bash)

 Supporting Layers

 - /tools/ - Reusable API clients and utilities
 - /context/ - Dynamic runtime state and session tracking
 - /knowledge/ - Static templates, prompts, and guidelines

 ---
 Directory Structure

 /Users/jeancs/Projects/gdg/
 ├── AGENTS.md                          # Orchestrator with routing logic
 ├── README.md                          # Project documentation
 ├── .env.example                       # Environment template
 ├── .gitignore                         # Git ignore patterns
 ├── requirements.txt                   # Python dependencies
 │
 ├── directives/                        # Declarative workflow plans
 │   ├── newsletter-generation.md       # Main newsletter workflow
 │   ├── audio-extraction.md           # Audio download workflow
 │   ├── transcription.md              # Transcription workflow
 │   └── content-generation.md         # AI generation workflow
 │
 ├── execution/                         # Executable scripts
 │   ├── orchestrator.sh               # Main entry point (bash)
 │   ├── pipeline.py                   # Python orchestration
 │   ├── extract_audio.py              # YouTube audio extraction
 │   ├── transcribe_audio.py           # Whisper API integration
 │   ├── generate_summaries.py         # AI summaries (configurable provider)
 │   └── generate_newsletter.py        # Final newsletter generation
 │
 ├── tools/                            # Reusable utilities
 │   ├── youtube_downloader.py         # yt-dlp wrapper
 │   ├── whisper_client.py             # OpenAI Whisper API client
 │   ├── ai_client.py                  # Multi-provider AI client (Claude/OpenAI/Gemini)
 │   ├── file_utils.py                 # File operations
 │   └── error_handler.py              # Error handling with retries
 │
 ├── context/                          # Dynamic runtime data
 │   ├── sessions/                     # Session-specific data
 │   ├── current_processing.json       # Current run state
 │   └── processing_history.json       # Past runs log
 │
 ├── knowledge/                        # Static domain knowledge
 │   ├── newsletter_templates/
 │   │   ├── template.md               # Base newsletter structure
 │   │   ├── tone_guidelines.md        # Voice and style guide
 │   │   └── structure_requirements.md # Format specifications
 │   ├── prompts/
 │   │   ├── summary_prompt.md         # Talk summary prompt
 │   │   └── newsletter_prompt.md      # Newsletter generation prompt
 │   └── examples/
 │       └── 2024-12-newsletter.md     # Reference example
 │
 ├── output/                           # Generated newsletters
 └── temp/                             # Temporary processing files
     ├── audio/                        # Downloaded audio files
     └── transcripts/                  # Raw transcripts

 ---
 Critical Files & Their Purposes

 Core Orchestration

 AGENTS.md - Central orchestrator defining:
 - Agent roles (Newsletter Orchestrator, Audio Extraction Agent, Transcription Agent, Content Generation Agent)
 - Routing logic and decision tree
 - State management rules
 - Error handling strategies
 - Resume-from-failure behavior

 execution/orchestrator.sh - Entry point bash script:
 - Environment validation (check .env for API keys)
 - Dependency checks (yt-dlp, python, venv)
 - Input validation (2 YouTube URLs)
 - Calls Python pipeline
 - Exit with clear error messages

 execution/pipeline.py - Main Python coordinator:
 - Manages state in /context/current_processing.json
 - Calls specialized scripts in sequence
 - Handles retries and error recovery
 - Logs progress to stdout and file
 - Tracks costs across all API calls

 API Integration Tools

 tools/youtube_downloader.py - yt-dlp wrapper:
 class YouTubeDownloader:
     def download_audio(url: str, format: str = 'm4a') -> dict
     def get_video_info(url: str) -> dict
     def validate_url(url: str) -> bool

 tools/whisper_client.py - OpenAI Whisper client:
 class WhisperClient:
     def transcribe(audio_path: str, language: str = 'pt') -> dict
     def estimate_cost(audio_duration: float) -> float

 tools/ai_client.py - Multi-provider AI client:
 class AIClient:
     def __init__(provider: str, api_key: str)  # provider: 'claude', 'openai', 'gemini'
     def generate(prompt: str, max_tokens: int) -> dict
     def generate_with_context(system: str, user: str, files: list) -> dict

     # Internally routes to:
     # - ClaudeClient (Anthropic API)
     # - OpenAIClient (GPT-4/GPT-4o)
     # - GeminiClient (Google Generative AI)

 tools/error_handler.py - Centralized error handling:
 class ErrorHandler:
     def retry_with_backoff(func, max_retries=3, backoff_factor=2.0)
     def handle_api_error(error: Exception) -> dict

 Execution Scripts

 execution/extract_audio.py:
 - Validates YouTube URLs
 - Downloads audio using YouTubeDownloader tool
 - Saves to /temp/audio/{video_id}.m4a
 - Logs metadata (duration, title)
 - Updates context state

 execution/transcribe_audio.py:
 - Processes audio files from /temp/audio/
 - Calls WhisperClient with language='pt'
 - Saves transcripts to /temp/transcripts/{video_id}_transcript.txt
 - Tracks API costs
 - Handles rate limiting and retries

 execution/generate_summaries.py:
 - Loads transcripts
 - Loads /knowledge/prompts/summary_prompt.md
 - Calls AIClient (provider from .env) for each talk
 - Saves to /temp/summaries/{video_id}_summary.md

 execution/generate_newsletter.py:
 - Loads all summaries and transcripts
 - Loads newsletter template from /knowledge/newsletter_templates/
 - Loads tone guidelines
 - Compiles context for AI generation
 - Calls AIClient (provider from .env)
 - Generates final newsletter
 - Saves to /output/YYYY-MM-newsletter.md

 Knowledge Base (User Provides Content)

 knowledge/newsletter_templates/template.md:
 - Newsletter structure with sections
 - Placeholder format for talks
 - Standard headers and footers
 - User will copy from Claude.ai project

 knowledge/newsletter_templates/tone_guidelines.md:
 - Voice and style guidelines (professional but friendly)
 - Portuguese-Brazilian language nuances
 - Technical writing standards
 - User will copy from Claude.ai project

 knowledge/prompts/summary_prompt.md:
 - System prompt for talk summarization
 - Provider-agnostic instructions on format and tone
 - Key points to extract (main topic, concepts, takeaways)

 knowledge/prompts/newsletter_prompt.md:
 - System prompt for newsletter generation
 - Template integration instructions
 - Quality criteria (length, structure, engagement)

 State Management

 context/current_processing.json:
 {
   "session_id": "2026-01-newsletter",
   "status": "in_progress",
   "current_step": "transcription",
   "videos": [
     {
       "url": "https://youtube.com/...",
       "video_id": "xxx",
       "status": "transcribed",
       "audio_path": "/temp/audio/xxx.m4a",
       "transcript_path": "/temp/transcripts/xxx_transcript.txt",
       "costs": {"transcription": 0.36}
     }
   ],
   "total_cost": 0.36
 }

 Enables resume-from-failure: if script crashes, can restart from last successful step.

 ---
 Workflow Diagram

 User runs: ./orchestrator.sh <url1> <url2>
     ↓
 AGENTS.md loads → checks state → determines routing
     ↓
 pipeline.py coordinates sequential execution
     ↓
 ┌─────────────────────────────────────────────┐
 │ Step 1: Audio Extraction                    │
 │ Directive: directives/audio-extraction.md   │
 │ Script: execution/extract_audio.py          │
 │ Tool: tools/youtube_downloader.py           │
 │ Output: temp/audio/*.m4a                    │
 └─────────────────┬───────────────────────────┘
                   ↓
 ┌─────────────────────────────────────────────┐
 │ Step 2: Transcription                       │
 │ Directive: directives/transcription.md      │
 │ Script: execution/transcribe_audio.py       │
 │ Tool: tools/whisper_client.py               │
 │ Output: temp/transcripts/*.txt              │
 │ Cost: ~$0.36 per 1-hour talk                │
 └─────────────────┬───────────────────────────┘
                   ↓
 ┌─────────────────────────────────────────────┐
 │ Step 3: Summary Generation                  │
 │ Directive: directives/content-generation.md │
 │ Script: execution/generate_summaries.py     │
 │ Tool: tools/ai_client.py (configurable)     │
 │ Prompt: knowledge/prompts/summary_prompt.md │
 │ Output: temp/summaries/*.md                 │
 └─────────────────┬───────────────────────────┘
                   ↓
 ┌─────────────────────────────────────────────┐
 │ Step 4: Newsletter Generation               │
 │ Directive: directives/content-generation.md │
 │ Script: execution/generate_newsletter.py    │
 │ Tool: tools/ai_client.py (configurable)     │
 │ Template: knowledge/newsletter_templates/   │
 │ Prompt: knowledge/prompts/newsletter_prompt │
 │ Output: output/YYYY-MM-newsletter.md        │
 └─────────────────┬───────────────────────────┘
                   ↓
 Update context/processing_history.json
 Display summary: paths, costs, duration

 ---
 Implementation Steps

 Phase 1: Foundation Setup

 1. Create directory structure
 mkdir -p directives execution tools context/sessions knowledge/{newsletter_templates,prompts,examples} output temp/{audio,transcripts,summaries}
 2. Initialize Python environment
 python3 -m venv venv
 source venv/bin/activate
 3. Create requirements.txt
 anthropic==0.47.0
 openai==1.59.7
 google-generativeai==0.8.3
 yt-dlp==2024.12.13
 python-dotenv==1.0.0
 pydantic==2.10.5
 4. Install dependencies
 pip install -r requirements.txt
 brew install yt-dlp  # if not already installed
 5. Create .env file
 # Transcription (required)
 OPENAI_API_KEY=sk-...

 # AI Provider Configuration (choose one)
 AI_PROVIDER=claude  # Options: 'claude', 'openai', 'gemini'

 # Provider API Keys (add the one you're using)
 ANTHROPIC_API_KEY=sk-ant-...  # For Claude
 # OPENAI_API_KEY already set above for Whisper (also used for GPT)
 GOOGLE_API_KEY=...  # For Gemini

 # Optional
 LOG_LEVEL=INFO
 6. Create .gitignore
 venv/
 .env
 temp/
 output/
 context/
 __pycache__/
 *.pyc

 Phase 2: Orchestration Files

 7. Write AGENTS.md - Define orchestrator logic:
   - Agent roles and responsibilities
   - Decision tree (validate → extract → transcribe → summarize → generate)
   - Routing rules to directives
   - State management strategy
   - Error handling and retry policies
 8. Write directive files:
   - directives/newsletter-generation.md - Overall workflow
   - directives/audio-extraction.md - Audio download steps
   - directives/transcription.md - Transcription process
   - directives/content-generation.md - AI generation workflow

 Phase 3: Core Tools (Critical Path)

 9. Implement tools/error_handler.py (foundation):
   - retry_with_backoff() - exponential backoff retry
   - handle_api_error() - API-specific error handling
   - Logging utilities
 10. Implement tools/youtube_downloader.py:
   - YouTubeDownloader class
   - download_audio() using yt-dlp subprocess
   - validate_url() for URL checking
   - get_video_info() for metadata
   - Error handling with ErrorHandler
 11. Implement tools/whisper_client.py:
   - WhisperClient class
   - transcribe() method calling OpenAI API
   - estimate_cost() helper
   - Rate limiting handling (429 errors)
   - Error handling with retries
 12. Implement tools/ai_client.py:
   - AIClient class with provider parameter ('claude', 'openai', 'gemini')
   - generate() method for basic generation (unified interface)
   - generate_with_context() for multi-file context
   - Internal provider-specific clients:
       - _ClaudeProvider - Anthropic API integration
     - _OpenAIProvider - OpenAI GPT-4/GPT-4o integration
     - _GeminiProvider - Google Gemini API integration
   - Cost tracking from usage metadata (provider-specific)
   - Unified error handling across providers
 13. Implement tools/file_utils.py:
   - ensure_directory() - create dirs if needed
   - read_file(), write_file() with error handling
   - get_file_hash() for deduplication
   - cleanup_temp_files()

 Phase 4: Execution Scripts

 14. Implement execution/extract_audio.py:
 import sys
 from tools.youtube_downloader import YouTubeDownloader
 from tools.error_handler import ErrorHandler

 def main(video_urls: list):
     downloader = YouTubeDownloader(output_dir='temp/audio')
     for url in video_urls:
         result = downloader.download_audio(url)
         # Update context/current_processing.json
         # Log metadata
 15. Implement execution/transcribe_audio.py:
 from tools.whisper_client import WhisperClient

 def main(audio_files: list):
     client = WhisperClient(api_key=os.getenv('OPENAI_API_KEY'))
     for audio_file in audio_files:
         result = client.transcribe(audio_file, language='pt')
         # Save to temp/transcripts/
         # Update context with costs
 16. Implement execution/generate_summaries.py:
 from tools.ai_client import AIClient

 def main(transcript_files: list):
     provider = os.getenv('AI_PROVIDER', 'claude')
     client = AIClient(provider=provider)
     prompt = load_file('knowledge/prompts/summary_prompt.md')
     for transcript in transcript_files:
         summary = client.generate(prompt + transcript)
         # Save to temp/summaries/
 17. Implement execution/generate_newsletter.py:
 from tools.ai_client import AIClient

 def main(summaries: list):
     provider = os.getenv('AI_PROVIDER', 'claude')
     client = AIClient(provider=provider)
     template = load_file('knowledge/newsletter_templates/template.md')
     tone = load_file('knowledge/newsletter_templates/tone_guidelines.md')
     prompt = load_file('knowledge/prompts/newsletter_prompt.md')

     newsletter = client.generate_with_context(
         system=prompt + tone,
         user=f"Generate newsletter using: {summaries}",
         context_files=[template]
     )
     # Save to output/YYYY-MM-newsletter.md
 18. Implement execution/pipeline.py (coordinator):
 import json
 from pathlib import Path

 def load_state():
     # Load context/current_processing.json

 def save_state(state):
     # Save context/current_processing.json

 def main(video_urls: list):
     state = load_state() or initialize_state(video_urls)

     if state['current_step'] in ['pending', 'audio_extraction']:
         extract_audio.main(video_urls)
         state['current_step'] = 'transcription'
         save_state(state)

     if state['current_step'] == 'transcription':
         transcribe_audio.main(get_audio_files())
         state['current_step'] = 'summary'
         save_state(state)

     if state['current_step'] == 'summary':
         generate_summaries.main(get_transcript_files())
         state['current_step'] = 'newsletter'
         save_state(state)

     if state['current_step'] == 'newsletter':
         generate_newsletter.main(get_summary_files())
         state['status'] = 'completed'
         save_state(state)
         update_history(state)

     print_summary(state)
 19. Implement execution/orchestrator.sh:
 #!/bin/bash
 set -e

 # Validate environment
 if [ ! -f .env ]; then
     echo "Error: .env file not found"
     exit 1
 fi

 # Check dependencies
 command -v yt-dlp >/dev/null 2>&1 || { echo "yt-dlp not installed"; exit 1; }

 # Activate venv
 source venv/bin/activate

 # Run pipeline
 python execution/pipeline.py "$@"

 Phase 5: Knowledge Base Setup

 20. USER ACTION: Create knowledge files
   - Copy newsletter guidelines from Claude.ai project
   - Create knowledge/newsletter_templates/template.md
   - Create knowledge/newsletter_templates/tone_guidelines.md
   - Create knowledge/newsletter_templates/structure_requirements.md
 21. Write AI prompts:
   - knowledge/prompts/summary_prompt.md - Talk summarization instructions
   - knowledge/prompts/newsletter_prompt.md - Newsletter generation instructions
 22. Add example (optional):
   - knowledge/examples/2024-12-newsletter.md - Reference output

 Phase 6: Polish & Documentation

 20. Write README.md:
   - Project overview
   - Setup instructions
   - AI provider configuration options
   - Usage: ./execution/orchestrator.sh <url1> <url2>
   - Cost breakdown per provider
   - Troubleshooting
 21. Manual end-to-end test:
   - Test with 2 real YouTube videos
   - Verify each step completes
   - Check output quality
   - Validate cost tracking
   - Test switching between AI providers

 ---
 API Configuration & Error Handling

 OpenAI Whisper API

 - Endpoint: https://api.openai.com/v1/audio/transcriptions
 - Authentication: Bearer token (OPENAI_API_KEY)
 - Model: whisper-1
 - Language: pt (Portuguese)
 - Cost: $0.006/minute
 - File size limit: 25MB
 - Timeout: 120 seconds
 - Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
 - Rate limit handling: Wait on 429, retry after delay

 AI Provider Configuration (Configurable)

 Claude (Anthropic):
 - Endpoint: https://api.anthropic.com/v1/messages
 - Authentication: x-api-key header (ANTHROPIC_API_KEY)
 - Model: claude-sonnet-4-5-20250929
 - Max tokens: 4096 (summaries), 8192 (newsletter)
 - Cost: ~$3/$15 per million tokens (input/output)
 - Timeout: 60 seconds
 - Retry: 3 attempts with backoff

 OpenAI GPT:
 - Endpoint: https://api.openai.com/v1/chat/completions
 - Authentication: Bearer token (OPENAI_API_KEY)
 - Model: gpt-4o or gpt-4-turbo
 - Max tokens: 4096 (summaries), 8192 (newsletter)
 - Cost: ~$2.50/$10 per million tokens (gpt-4o)
 - Timeout: 60 seconds
 - Retry: 3 attempts with backoff

 Gemini (Google):
 - Endpoint: https://generativelanguage.googleapis.com/v1beta/models/gemini-pro
 - Authentication: API key (GOOGLE_API_KEY)
 - Model: gemini-1.5-pro or gemini-2.0-flash
 - Max tokens: 8192
 - Cost: Free tier available, then ~$0.35/$1.05 per million tokens
 - Timeout: 60 seconds
 - Retry: 3 attempts with backoff

 Error Recovery Strategy

 State-based resume:
 - Save state after each major step
 - On restart, check context/current_processing.json
 - Resume from current_step field
 - Force restart: --force-restart flag

 Error categories:
 1. Transient (network, timeout): Retry with backoff
 2. API quota: Log error, save state, exit gracefully
 3. Invalid input: Skip item, continue with remaining
 4. Fatal (auth, disk space): Exit with clear message

 ---
 Usage

 First Time Setup

 # 1. Create .env file with API keys
 cp .env.example .env
 # Edit .env and add your keys

 # 2. Install dependencies
 python3 -m venv venv
 source venv/bin/activate
 pip install -r requirements.txt
 brew install yt-dlp

 # 3. Copy newsletter guidelines from Claude.ai project
 # Paste into knowledge/newsletter_templates/*.md files

 # 4. Make orchestrator executable
 chmod +x execution/orchestrator.sh

 Running the Pipeline

 # Activate environment
 source venv/bin/activate

 # Run with 2 YouTube URLs
 ./execution/orchestrator.sh \
   "https://www.youtube.com/watch?v=VIDEO1_ID" \
   "https://www.youtube.com/watch?v=VIDEO2_ID"

 # Output will be in: output/YYYY-MM-newsletter.md

 Resume from Failure

 If the script crashes mid-execution:
 # State is saved in context/current_processing.json
 # Just run again with same URLs - will resume from last step
 ./execution/orchestrator.sh <same urls>

 # Or force restart from beginning:
 ./execution/orchestrator.sh --force-restart <urls>

 ---
 Verification & Testing

 Manual Testing Checklist

 Pre-execution:
 - .env file exists with valid API keys
 - yt-dlp installed and accessible
 - Python venv activated
 - All dependencies installed
 - Knowledge base files created (templates, prompts)

 Test Run 1 - Happy Path:
 - Run with 2 valid YouTube URLs (pt-br talks)
 - Verify audio files downloaded to temp/audio/
 - Verify transcripts created in temp/transcripts/
 - Verify summaries created in temp/summaries/
 - Verify final newsletter in output/YYYY-MM-newsletter.md
 - Check newsletter follows template structure
 - Check newsletter matches tone guidelines
 - Verify cost tracking in context/processing_history.json

 Test Run 2 - Error Handling:
 - Test with 1 valid, 1 invalid URL
 - Verify pipeline continues with valid video
 - Verify error logged in state
 - Test resume-from-failure (kill process mid-transcription)
 - Restart and verify resumes from correct step

 Test Run 3 - Edge Cases:
 - Test with very long video (>1 hour)
 - Test with video containing heavy technical jargon
 - Test with poor audio quality video
 - Verify costs are within expected range

 Output Quality Checks:
 - Newsletter is valid markdown
 - Both talks are included
 - Talk summaries are accurate and coherent
 - Portuguese grammar and spelling correct
 - Technical terms properly explained
 - Follows community tone (friendly, professional)
 - Length is appropriate (800-1200 words)
 - YouTube links included
 - Proper formatting (headers, bullets, emphasis)

 Cost Validation

 Expected costs for 2 talks (1 hour each):
 - Whisper transcription: 2 × $0.36 = $0.72 (fixed)

 AI Provider Costs (variable):
 - Claude: 2 summaries (~$0.40) + newsletter (~$0.30) = $0.70 → Total: $1.42/month
 - OpenAI GPT-4o: 2 summaries (~$0.30) + newsletter (~$0.25) = $0.55 → Total: $1.27/month
 - Gemini: 2 summaries (~$0.15) + newsletter (~$0.15) = $0.30 → Total: $1.02/month (or free tier)

 Verify actual costs in context/processing_history.json match expectations.

 ---
 Success Criteria

 The implementation is complete and successful when:

 1. Functional:
   - ✅ Accepts 2 YouTube URLs as input
   - ✅ Downloads audio from both videos
   - ✅ Transcribes audio to Portuguese text
   - ✅ Generates individual talk summaries
   - ✅ Produces final newsletter in markdown
   - ✅ Newsletter follows user's template and tone
 2. Reliable:
   - ✅ Handles network errors gracefully with retries
   - ✅ Resumes from last successful step on failure
   - ✅ Validates inputs before processing
   - ✅ Logs errors with context for debugging
 3. Observable:
   - ✅ Tracks processing state in /context/
   - ✅ Logs progress to stdout
   - ✅ Reports costs per step and total
   - ✅ Provides clear error messages
 4. Quality:
   - ✅ Output newsletter is coherent and accurate
   - ✅ Follows tone and structure guidelines
   - ✅ Contains no placeholder text or obvious errors
   - ✅ Valid markdown format
 5. Maintainable:
   - ✅ Clear separation of concerns (orchestrator/directives/execution)
   - ✅ Documented with README and code comments
   - ✅ Easy to modify templates without touching code
   - ✅ Easy to switch AI providers via .env configuration

 ---
 Future Extensibility

 Architecture supports future enhancements:

 1. Multiple talks: Update state schema to handle N videos
 2. HTML output: Add tools/html_formatter.py
 3. Email integration: Add email sending script
 4. Scheduled runs: Add cron job with playlist monitoring
 5. Quality review: Add human-in-the-loop approval step
 6. Multi-language: Add language detection and lang-specific prompts
 7. Analytics dashboard: Track costs, processing time, quality metrics

 ---
 Key Architectural Decisions

 1. Orchestrator Pattern

 Decision: Use AGENTS.md → directives → execution hierarchy
 Rationale: Separates decision logic from implementation, allowing non-developers to modify workflows via markdown directives without touching code.

 2. Stateful Processing

 Decision: Store processing state in context/current_processing.json
 Rationale: Enables resume-from-failure for long-running pipelines with expensive API calls. Critical for reliability.

 3. Two-Phase AI Generation

 Decision: Separate summary and newsletter generation steps
 Rationale: Provides checkpoint for review, enables summary reuse, allows iterative refinement without re-transcription.

 4. Python + Bash Hybrid

 Decision: Bash entry point, Python for execution
 Rationale: Bash provides simple environment validation and process management, Python offers superior API integration and error handling.

 5. Knowledge Base Separation

 Decision: Static templates/prompts in /knowledge/, dynamic state in /context/
 Rationale: Allows non-technical updates to newsletter style and prompts without code changes. Supports iterative refinement.

 ---
 Implementation Timeline

 - Phase 1 (Foundation): 2-3 hours - Directory setup, dependencies, environment
 - Phase 2 (Orchestration): 1-2 hours - AGENTS.md and directive files
 - Phase 3 (Tools): 5-7 hours - Multi-provider AI client and utilities (most code-heavy)
 - Phase 4 (Execution): 3-4 hours - Pipeline scripts and orchestrator
 - Phase 5 (Knowledge): 1 hour - User creates templates from Claude.ai project
 - Phase 6 (Polish): 1-2 hours - README and end-to-end testing

 Total: ~13-19 hours for complete implementation.
