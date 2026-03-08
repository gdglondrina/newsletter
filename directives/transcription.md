# Transcription Directive

## Purpose

Convert audio files to text using OpenAI Whisper API.

## Script

`execution/transcribe_audio.py`

## Tool

`tools/whisper_client.py`

## Input

- Audio files from `temp/audio/` referenced in state

## Process

1. **File Validation**
   - Verify audio file exists
   - Check file size (must be < 25MB)
   - For large files, consider splitting (not implemented)

2. **API Call**
   - Send audio to Whisper API
   - Specify language: Portuguese (pt)
   - Request text format output

3. **Transcript Processing**
   - Receive transcription text
   - Save to `temp/transcripts/{video_id}_transcript.txt`
   - Track API cost

4. **State Update**
   - Record transcript path
   - Update video status to "transcribed"
   - Add transcription cost
   - Save checkpoint

## Output

- Transcript files: `temp/transcripts/{video_id}_transcript.txt`
- Cost tracking in state

## API Configuration

- Endpoint: OpenAI Whisper API
- Model: whisper-1
- Language: pt (Portuguese)
- Format: text

## Cost

$0.006 per minute of audio

Example: 60-minute talk = $0.36

## Error Handling

| Error | Action |
|-------|--------|
| Rate limit (429) | Wait and retry with backoff |
| File too large | Log error, skip video |
| Invalid API key | Fatal error, stop pipeline |
| Timeout | Retry up to 3 times |

## Dependencies

- OpenAI API key (OPENAI_API_KEY)
- openai Python package

## Performance Notes

- Processing time: ~1-2 minutes per 1-hour audio
- API timeout set to 120 seconds
- Retries use exponential backoff

## Resume Behavior

If transcript file already exists for a video ID, skip transcription.
