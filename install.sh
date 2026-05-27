#!/usr/bin/env bash
# llm-instill-wiki installer
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Laggom/llm-instill-wiki/main/install.sh | bash
# Or, after cloning the repo manually:
#   bash install.sh

set -euo pipefail

REPO_URL="https://github.com/Laggom/llm-instill-wiki.git"
TARGET_DIR="llm-instill-wiki"

# --- Step 1: ensure we're inside the repo --------------------------------
in_repo=0
if [ -f CLAUDE.md ] && grep -q "LLM Wiki Operating Schema" CLAUDE.md 2>/dev/null; then
    in_repo=1
fi

if [ "$in_repo" -eq 0 ]; then
    if [ -d "$TARGET_DIR" ]; then
        echo "ERROR: directory '$TARGET_DIR' already exists." >&2
        echo "       cd into it and rerun, or remove it first." >&2
        exit 1
    fi
    if ! command -v git >/dev/null 2>&1; then
        echo "ERROR: git is required but not found." >&2
        exit 1
    fi
    echo "Cloning into ./$TARGET_DIR ..."
    git clone --quiet "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

# --- Step 2: verify Python 3.10+ -----------------------------------------
PY=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
            PY="$cmd"
            break
        fi
    fi
done
if [ -z "$PY" ]; then
    echo "ERROR: Python 3.10+ is required but was not found in PATH." >&2
    exit 1
fi
echo "Python: $($PY --version)"

# --- Step 3: create content directories ----------------------------------
mkdir -p raw wiki/sources wiki/concepts wiki/entities instill

# --- Step 4: scaffold wiki/index.md and wiki/log.md (only if missing) ---
if [ ! -f wiki/index.md ]; then
    cat > wiki/index.md <<'EOF'
# Index

## Sources

## Concepts

## Entities
EOF
    echo "Created wiki/index.md"
fi

if [ ! -f wiki/log.md ]; then
    echo "# Log" > wiki/log.md
    echo "Created wiki/log.md"
fi

# --- Step 5: smoke-test the scheduler ------------------------------------
"$PY" tools/instill_sched.py stats >/dev/null

# --- Done ----------------------------------------------------------------
HERE=$(basename "$PWD")
cat <<EOF

✓ Setup complete.

Next steps:
  1. cd $HERE   (if not already)
  2. Drop a source file into raw/
  3. Open this directory in Claude Code, or any AGENTS.md / GEMINI.md compatible agent
  4. Tell the agent: "raw/<your-file>.md ingest 해줘"

See README.md for the full guide.
EOF
