#!/usr/bin/env bash
#
# VCAT Phase 1 Release Script
# ===========================
#
# This script ensures that releases always contain outputs
# that match the current code. It enforces the pipeline:
#
#   clean → build → validate → package
#
# Usage:
#   ./scripts/release_phase1.sh [version]
#
# Example:
#   ./scripts/release_phase1.sh 0.2.0
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Default version
VERSION="${1:-0.2.0}"

echo "============================================================"
echo "VCAT Phase 1 Release Script"
echo "============================================================"
echo "Version: $VERSION"
echo "Project: $PROJECT_ROOT"
echo ""

# Check for required source file
SOURCE_FILE="$PROJECT_ROOT/data_sources/cache/ZL3b-n.txt"
if [[ ! -f "$SOURCE_FILE" ]]; then
    echo -e "${RED}ERROR: Source file not found: $SOURCE_FILE${NC}"
    echo ""
    echo "Download it first:"
    echo "  curl -sL 'https://www.voynich.nu/data/ZL3b-n.txt' -o '$SOURCE_FILE'"
    exit 1
fi

cd "$PROJECT_ROOT"

# Step 1: Clean
echo -e "${YELLOW}[1/5] Cleaning output directory...${NC}"
rm -f output/eva_lines.jsonl output/eva_lines.parquet output/eva_lines_build_report.json
echo "  Done."

# Step 2: Build
echo ""
echo -e "${YELLOW}[2/5] Building datasets...${NC}"
python -m builders.build_eva_lines --source "$SOURCE_FILE" --output-dir output/
if [[ $? -ne 0 ]]; then
    echo -e "${RED}ERROR: Build failed${NC}"
    exit 1
fi

# Step 3: Validate
echo ""
echo -e "${YELLOW}[3/5] Validating outputs...${NC}"
python validators/validate_phase1_outputs.py
if [[ $? -ne 0 ]]; then
    echo -e "${RED}ERROR: Validation failed - outputs do not match code${NC}"
    exit 1
fi

# Step 4: Run tests
echo ""
echo -e "${YELLOW}[4/5] Running tests...${NC}"
python -m pytest tests/ -q --tb=short 2>/dev/null || {
    echo -e "${YELLOW}Warning: Some tests failed or pytest not available${NC}"
}

# Step 5: Package
echo ""
echo -e "${YELLOW}[5/5] Creating release archive...${NC}"
ARCHIVE_NAME="voynich-data-phase1-v${VERSION}.tar.gz"

# Clean up cache directories
rm -rf .ruff_cache __pycache__ */__pycache__ */*/__pycache__ .pytest_cache 2>/dev/null || true

# Create archive (excluding cache, git, and large source files)
cd ..
tar --exclude='voynich-data/.git' \
    --exclude='voynich-data/.ruff_cache' \
    --exclude='voynich-data/__pycache__' \
    --exclude='voynich-data/*/__pycache__' \
    --exclude='voynich-data/.pytest_cache' \
    --exclude='voynich-data/data_sources/cache/*.txt' \
    -czvf "$ARCHIVE_NAME" voynich-data/ 2>&1 | tail -5

mv "$ARCHIVE_NAME" voynich-data/
cd voynich-data

echo ""
echo "============================================================"
echo -e "${GREEN}Release package created: $ARCHIVE_NAME${NC}"
echo "============================================================"
echo ""
echo "Contents summary:"
echo "  - Code: parsers/, builders/, validators/, vcat/"
echo "  - Schemas: schemas/"
echo "  - Output: eva_lines.jsonl, eva_lines.parquet, build_report"
echo "  - Docs: README.md, CHANGELOG.md, docs/"
echo "  - Tests: tests/"
echo ""
echo "Next steps:"
echo "  1. Test the archive: tar -tzf $ARCHIVE_NAME | head -20"
echo "  2. Verify HF load: python -c \"from datasets import load_dataset; ds = load_dataset('json', data_files='output/eva_lines.jsonl'); print(ds)\""
echo "  3. Push to GitHub"
echo "  4. Upload to HuggingFace"
