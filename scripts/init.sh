#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROJECT_ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT_DIR"

pip install -r requirements.txt

python "$PROJECT_ROOT_DIR/nlp/init_translation.py"

