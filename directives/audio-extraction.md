# Audio Extraction Directive

## Purpose

Download audio from YouTube videos for transcription.

## Script

`execution/extract_audio.py`

## Tool

`tools/youtube_downloader.py`

## Input

- List of YouTube video URLs from state or command line

## Process

1. **URL Validation**
   - Check URL format matches YouTube patterns
   - Extract video ID from URL

2. **Video Info Retrieval**
   - Get video metadata (title, duration, channel)
   - Verify video is accessible
   - Estimate file size

3. **Audio Download**
   - Use yt-dlp to extract audio
   - Save as M4A format (best quality/size ratio)
   - Store in `temp/audio/{video_id}.m4a`

4. **State Update**
   - Record audio path, duration, title
   - Set video status to "audio_extracted"
   - Save checkpoint

## Output

- Audio files: `temp/audio/{video_id}.m4a`
- Updated state with video metadata

## Error Handling

| Error | Action |
|-------|--------|
| Invalid URL | Skip video, log error |
| Private video | Skip video, log error |
| Network timeout | Retry with backoff |
| yt-dlp not installed | Fatal error, stop pipeline |

## Dependencies

- yt-dlp (system command)
- Network access to YouTube

## Performance Notes

- Downloads run sequentially (one video at a time)
- Typical 1-hour video: 30-50 MB audio
- Download time: ~1-3 minutes per video

## Resume Behavior

If audio file already exists for a video ID, skip download.
