export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tree-signal"
mkdir -p "$UV_PROJECT_ENVIRONMENT"
export UV_CACHE_DIR="$HOME/.cache/uv"
mkdir -p "$UV_CACHE_DIR"
source $HOME/.venvs/tree-signal/bin/activate
which python
