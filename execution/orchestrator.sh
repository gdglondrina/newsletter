#!/bin/bash
#
# GDG Newsletter Automation - Entry Point
#
# Usage:
#   ./orchestrator.sh <youtube_url_1> <youtube_url_2>
#   ./orchestrator.sh --force-restart <url1> <url2>
#
# This script:
# 1. Validates the environment
# 2. Activates the Python virtual environment
# 3. Runs the Python pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory (handles symlinks)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   GDG Newsletter Automation Pipeline       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Create .env from .env.example and add your API keys:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your API keys"
    exit 1
fi

# Check for required commands
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: $1 not installed${NC}"
        echo "$2"
        exit 1
    fi
}

check_command "python3" "Install Python 3: brew install python3"
check_command "yt-dlp" "Install yt-dlp: brew install yt-dlp"

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo -e "${GREEN}Virtual environment created and dependencies installed.${NC}"
else
    source venv/bin/activate
fi

# Verify key dependencies are installed
python3 -c "import openai" 2>/dev/null || {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -r requirements.txt
}

# Show configuration
echo -e "${GREEN}Configuration:${NC}"
echo "  Project: $PROJECT_ROOT"
echo "  Python: $(python3 --version)"
echo "  AI Model: $(grep '^AI_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo 'gpt-4o (default)')"
STT_MODEL=$(grep '^TRANSCRIPT_MODEL=' .env 2>/dev/null | cut -d= -f2 || echo 'whisper-1')
if [ "$STT_MODEL" = "faster-whisper" ]; then
    FW_SIZE=$(grep '^FASTER_WHISPER_SIZE=' .env 2>/dev/null | cut -d= -f2 || echo 'medium')
    STT_MODEL="$STT_MODEL ($FW_SIZE)"
fi
echo "  STT Model: $STT_MODEL"
echo ""

# Run the pipeline
echo -e "${GREEN}Starting pipeline...${NC}"
echo ""

python3 execution/pipeline.py "$@"

EXIT_CODE=$?

# Deactivate virtual environment
deactivate 2>/dev/null || true

exit $EXIT_CODE
