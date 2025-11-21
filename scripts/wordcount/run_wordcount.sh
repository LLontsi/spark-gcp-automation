#!/bin/bash

# WordCount Test Script for Spark Cluster
# This script runs the WordCount application to validate Spark deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}  Spark WordCount Test${NC}"
echo -e "${GREEN}==================================${NC}"

# Check if Spark is available
if ! command -v spark-submit &> /dev/null; then
    echo -e "${RED}Error: spark-submit not found${NC}"
    echo "Please ensure Spark is installed and in PATH"
    exit 1
fi

# Variables
MASTER_URL="${SPARK_MASTER_URL:-spark://spark-master:7077}"
INPUT_FILE="${1:-/tmp/sample_text.txt}"
OUTPUT_DIR="${2:-/tmp/wordcount_output}"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Master URL: $MASTER_URL"
echo "  Input File: $INPUT_FILE"
echo "  Output Dir: $OUTPUT_DIR"
echo ""

# Create sample input if not exists
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${YELLOW}Creating sample input file...${NC}"
    cat > "$INPUT_FILE" << 'EOF'
Apache Spark is a unified analytics engine for large-scale data processing.
Spark provides high-level APIs in Java, Scala, Python and R.
It also supports a rich set of higher-level tools including Spark SQL for SQL and structured data processing.
MLlib for machine learning, GraphX for graph processing, and Structured Streaming for incremental computation.
EOF
fi

# Remove old output
if [ -d "$OUTPUT_DIR" ]; then
    echo -e "${YELLOW}Removing old output directory...${NC}"
    rm -rf "$OUTPUT_DIR"
fi

echo -e "${GREEN}Running WordCount application...${NC}"

# Run WordCount (you'll implement the actual Spark job later)
spark-submit \
    --master "$MASTER_URL" \
    --deploy-mode client \
    --class WordCount \
    --executor-memory 1G \
    --total-executor-cores 2 \
    "$SCRIPT_DIR/wordcount.py" \
    "$INPUT_FILE" \
    "$OUTPUT_DIR"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}WordCount completed successfully!${NC}"
    echo -e "${YELLOW}Results:${NC}"
    if [ -f "$OUTPUT_DIR/part-00000" ]; then
        cat "$OUTPUT_DIR/part-00000"
    fi
else
    echo -e "${RED}WordCount failed!${NC}"
    exit 1
fi
