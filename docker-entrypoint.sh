#!/bin/bash
set -e

# Start the API server in the background
echo "Starting Tree Signal API server on port 8013..."
uvicorn tree_signal.api.main:app --host 0.0.0.0 --port 8013 &

# Start the static file server for the client
echo "Starting client server on port 8014..."
python -m http.server --directory client 8014 &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?
