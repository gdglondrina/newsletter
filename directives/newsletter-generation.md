# Newsletter Generation Workflow

## Overview

This directive describes the complete workflow for generating a monthly GDG newsletter from YouTube talk videos.

## Prerequisites

- Python virtual environment activated
- API keys configured in `.env`
- yt-dlp installed
- At least 2 YouTube video URLs

## Workflow Steps

### 1. Input Validation

**Entry Point**: User provides YouTube URLs via command line

**Validations**:
- URLs must be valid YouTube video URLs
- Videos must be publicly accessible
- Minimum 1 URL, recommended 2

**Routing**: → Audio Extraction

### 2. Audio Extraction

**Directive**: `audio-extraction.md`
**Outputs**: Audio files in `temp/audio/`

**Success Criteria**:
- Audio files downloaded for all valid URLs
- Metadata captured (title, duration)

**Routing**: → Transcription

### 3. Transcription

**Directive**: `transcription.md`
**Outputs**: Transcripts in `temp/transcripts/`

**Success Criteria**:
- Transcripts generated for all audio files
- Portuguese language detected correctly
- Costs tracked

**Routing**: → Content Generation (Summaries)

### 4. Summary Generation

**Directive**: `content-generation.md` (summary mode)
**Outputs**: Summaries in `temp/summaries/`

**Success Criteria**:
- Summaries follow template structure
- Key points extracted accurately
- Appropriate length (300-500 words per talk)

**Routing**: → Content Generation (Newsletter)

### 5. Newsletter Generation

**Directive**: `content-generation.md` (newsletter mode)
**Outputs**: Newsletter in `output/YYYY-MM-newsletter.md`

**Success Criteria**:
- Newsletter follows template
- All talks included
- Proper formatting
- Links preserved
- 800-1200 words total

**Routing**: → Complete

### 6. Completion

**Actions**:
- Save final state
- Update processing history
- Display cost summary
- Clean up temporary files (optional)

## Error Recovery

At any step failure:
1. State is automatically saved
2. Re-running the script resumes from last successful step
3. Individual video failures don't stop the pipeline

## Cost Estimation

For 2 one-hour talks:
- Transcription: ~$0.72
- Summaries: ~$0.30-0.70
- Newsletter: ~$0.20-0.40
- **Total**: ~$1.20-1.80

## Manual Intervention Points

1. **After summaries**: Review `temp/summaries/` before newsletter generation
2. **After newsletter**: Edit `output/YYYY-MM-newsletter.md` before publishing
