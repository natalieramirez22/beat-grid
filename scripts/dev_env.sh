# scripts/dev_env.sh  (make executable: chmod +x scripts/dev_env.sh)
#!/usr/bin/env bash
# Activate venv and set runtime loader path just for this shell session

source venv/bin/activate

# Homebrew fallback so pyo/libsndfile can find flac/vorbis/ogg
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib"

# (You already created the compatibility symlink; this is just extra safety.)
echo "Dev env ready. Python: $(python --version)"
