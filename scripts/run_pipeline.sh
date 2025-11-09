#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROJECT_ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT_DIR"

echo "Current working directory: $(pwd)"
echo "Starting Python pipeline script..."

python3 mitre_match.py \

EXIT_CODE=$? 
if [ $EXIT_CODE -eq 0 ]; then
    echo "Python pipeline script finished successfully at $(date)."
else
    echo "Python pipeline script failed with exit code $EXIT_CODE at $(date)."
fi