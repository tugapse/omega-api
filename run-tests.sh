#!/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Define the log file for the server output
SERVER_LOG="server.log"
# Define a file to store the server's process ID
SERVER_PID_FILE="server.pid"

# Function to clean up by killing the server process
cleanup() {
    echo "Cleaning up..."
    if [ -f $SERVER_PID_FILE ]; then
        PID=$(cat $SERVER_PID_FILE)
        echo "Killing server with PID: $PID"
        # Kill the process group to ensure all child processes are terminated
        kill -9 -- -$PID
        rm $SERVER_PID_FILE
    fi
    echo "Cleanup complete."
}

# Trap signals to ensure cleanup is always called
trap cleanup EXIT INT TERM

# Start the server in the background
# The `setsid` command runs the server in a new session, making it the leader of a new process group.
# This allows us to kill the entire process group later, preventing orphaned child processes.
echo "Starting server..."
(setsid uvicorn src.core.app:app --host 0.0.0.0 --port 8000 > $SERVER_LOG 2>&1 & echo $! > $SERVER_PID_FILE)
sleep 5 # Give the server a moment to start

# Check if the server started successfully
if ! [ -f $SERVER_PID_FILE ] || ! ps -p $(cat $SERVER_PID_FILE) > /dev/null; then
    echo "Server failed to start. Check $SERVER_LOG for details."
    cat $SERVER_LOG
    exit 1
fi

echo "Server started with PID $(cat $SERVER_PID_FILE). Running tests..."

# Run pytest
pytest -v tests/

echo "Tests finished."