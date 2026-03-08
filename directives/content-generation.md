# Content Generation Directive

## Purpose

Generate AI-powered content: individual talk summaries and final newsletter.

## Scripts

- `execution/generate_summaries.py` - Summary generation
- `execution/generate_newsletter.py` - Newsletter compilation

## Tool

`tools/ai_client.py` - Multi-provider AI client

## Modes

### Summary Mode

**Input**: Transcript files from `temp/transcripts/`

**Process**:
1. Load transcript for each video
2. Load summary prompt from `knowledge/prompts/summary_prompt.md`
3. Call AI provider with transcript and prompt
4. Save summary to `temp/summaries/{video_id}_summary.md`
5. Track cost and update state

**Output**: Summary files in `temp/summaries/`

**Quality Criteria**:
- 300-500 words per summary
- Structured with headers
- Key points extracted
- Technical accuracy maintained

### Newsletter Mode

**Input**: Summary files from `temp/summaries/`

**Process**:
1. Load all summaries
2. Load template from `knowledge/newsletter_templates/template.md`
3. Load tone guidelines from `knowledge/newsletter_templates/tone_guidelines.md`
4. Load newsletter prompt from `knowledge/prompts/newsletter_prompt.md`
5. Compile context and call AI provider
6. Save newsletter to `output/YYYY-MM-newsletter.md`
7. Track cost and finalize state

**Output**: Newsletter in `output/`

**Quality Criteria**:
- 800-1200 words total
- Follows template structure
- Consistent tone throughout
- All talks included with links
- Valid markdown formatting

## AI Provider Configuration

Provider is configured via `AI_PROVIDER` environment variable:

| Provider | API Key Variable | Model |
|----------|-----------------|-------|
| claude | ANTHROPIC_API_KEY | claude-sonnet-4-5-20250929 |
| openai | OPENAI_API_KEY | gpt-4o |
| gemini | GOOGLE_API_KEY | gemini-1.5-pro |

## Prompts

### Summary Prompt Structure

```
System: Instructions for summarizing talks
- Extract key points
- Identify technical concepts
- Note practical applications
- Maintain accuracy

User: Transcript of "{title}"
[transcript content]
```

### Newsletter Prompt Structure

```
System: Newsletter generation instructions
- Template structure
- Tone guidelines
- Quality criteria

User: Generate newsletter for {month} {year}
[summaries for all talks]
```

## Cost Estimation

| Provider | Summaries (2 talks) | Newsletter | Total |
|----------|---------------------|------------|-------|
| Claude | ~$0.40 | ~$0.30 | ~$0.70 |
| OpenAI | ~$0.30 | ~$0.25 | ~$0.55 |
| Gemini | ~$0.15 | ~$0.15 | ~$0.30 |

## Error Handling

| Error | Action |
|-------|--------|
| Rate limit | Retry with backoff |
| Invalid API key | Fatal error |
| Context too long | Truncate older content |
| Generation failed | Retry, then skip |

## Dependencies

- AI provider API key
- anthropic/openai/google-generativeai package

## Resume Behavior

- Summary mode: Skip videos that already have summary files
- Newsletter mode: Always regenerate (final step)

## Knowledge Base Files

Required (with defaults if missing):
- `knowledge/prompts/summary_prompt.md`
- `knowledge/prompts/newsletter_prompt.md`
- `knowledge/newsletter_templates/template.md`
- `knowledge/newsletter_templates/tone_guidelines.md`
