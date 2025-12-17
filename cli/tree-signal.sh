#!/usr/bin/env bash
# Tree Signal Bash CLI - Send messages from stdin to Tree Signal dashboard
# Usage: tail -f app.log | tree-signal [HOST:PORT] CHANNEL

set -euo pipefail

# Defaults
DEFAULT_URL="http://localhost:8013"
DEFAULT_SEVERITY="info"
SEVERITY=""
QUIET=false
DEBUG=false
DRY_RUN=false
API_KEY=""
API_URL=""
HOST_PORT=""
CHANNEL=""

# Load config file if it exists
load_config() {
    local config_file=""

    # Check config locations in order
    if [[ -n "${TREE_SIGNAL_CONFIG:-}" && -f "$TREE_SIGNAL_CONFIG" ]]; then
        config_file="$TREE_SIGNAL_CONFIG"
    elif [[ -f "$HOME/.config/tree-signal/config" ]]; then
        config_file="$HOME/.config/tree-signal/config"
    elif [[ -f "/etc/tree-signal/config" ]]; then
        config_file="/etc/tree-signal/config"
    fi

    if [[ -n "$config_file" ]]; then
        # shellcheck disable=SC1090
        source "$config_file"
        [[ "$DEBUG" == true ]] && echo "[DEBUG] Loaded config: $config_file" >&2
    fi
}

# Show help
show_help() {
    cat << 'EOF'
tree-signal.sh - Stream messages from stdin to Tree Signal dashboard

USAGE:
    tree-signal [OPTIONS] [HOST:PORT] CHANNEL

ARGUMENTS:
    CHANNEL              Hierarchical channel path (e.g., app.api.auth)
    HOST:PORT            Optional API host:port (default: from config/env)

OPTIONS:
    -s, --severity LEVEL Set severity: debug|info|warn|error (default: info)
    -q, --quiet          Suppress informational output
    -d, --debug          Enable debug output
    --dry-run            Print curl commands without sending
    -h, --help           Show this help

CONFIGURATION:
    Config file: ~/.config/tree-signal/config or /etc/tree-signal/config

    TREE_SIGNAL_URL      API base URL (default: http://localhost:8013)
    TREE_SIGNAL_API_KEY  API authentication key (optional)
    TREE_SIGNAL_CONFIG   Path to config file (optional)

EXAMPLES:
    # Simple - use default host
    echo "Deploy started" | tree-signal app.deploy
    tail -f app.log | tree-signal app.logs

    # Specify host:port
    echo "Error" | tree-signal localhost:8013 app.errors
    tail -f app.log | tree-signal 192.168.1.10:8013 app.logs

    # With filtering and severity
    tail -f app.log | grep ERROR | tree-signal -s error app.errors
    journalctl -fu nginx | tree-signal nginx.access

EXIT CODES:
    0    Success
    1    Configuration error
    2    API connection error
    3    Authentication error

EOF
}

# Parse arguments
parse_args() {
    local positional=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--severity)
                SEVERITY="$2"
                shift 2
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -*)
                echo "ERROR: Unknown option: $1" >&2
                echo "Use --help for usage information" >&2
                exit 1
                ;;
            *)
                positional+=("$1")
                shift
                ;;
        esac
    done

    # Parse positional arguments
    if [[ ${#positional[@]} -eq 0 ]]; then
        echo "ERROR: CHANNEL required" >&2
        echo "Use --help for usage information" >&2
        exit 1
    elif [[ ${#positional[@]} -eq 1 ]]; then
        # tree-signal CHANNEL
        CHANNEL="${positional[0]}"
    elif [[ ${#positional[@]} -eq 2 ]]; then
        # tree-signal HOST:PORT CHANNEL
        HOST_PORT="${positional[0]}"
        CHANNEL="${positional[1]}"
    else
        echo "ERROR: Too many arguments" >&2
        echo "Use --help for usage information" >&2
        exit 1
    fi
}

# Validate severity
validate_severity() {
    local sev="$1"
    case "$sev" in
        debug|info|warn|warning|error|critical)
            # Normalize: warning->warn, critical->error
            case "$sev" in
                warning) echo "warn" ;;
                critical) echo "error" ;;
                *) echo "$sev" ;;
            esac
            ;;
        *)
            echo "ERROR: Invalid severity: $sev (use: debug|info|warn|error)" >&2
            exit 1
            ;;
    esac
}

# Send message to API
send_message() {
    local channel="$1"
    local payload="$2"
    local severity="$3"
    local url="$4"

    # Build JSON payload (escape quotes in payload)
    local escaped_payload="${payload//\"/\\\"}"
    local json_payload="{\"channel\":\"$channel\",\"payload\":\"$escaped_payload\",\"severity\":\"$severity\"}"

    # Build curl command
    local curl_cmd=(
        curl
        -X POST
        -H "Content-Type: application/json"
        -s
        -w "\n%{http_code}"
        -o /dev/null
    )

    # Add API key header if configured
    if [[ -n "$API_KEY" ]]; then
        curl_cmd+=(-H "X-API-Key: $API_KEY")
    fi

    curl_cmd+=(-d "$json_payload")
    curl_cmd+=("$url/v1/messages")

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY-RUN] ${curl_cmd[*]}" >&2
        echo "[DRY-RUN] Payload: $json_payload" >&2
        return 0
    fi

    # Execute curl and capture HTTP status
    local http_code
    http_code=$("${curl_cmd[@]}" 2>/dev/null || echo "000")
    http_code="${http_code##*$'\n'}"  # Get last line (the status code)
    http_code="${http_code// /}"       # Remove any spaces

    # Check HTTP response
    case "$http_code" in
        200|201|202)
            [[ "$DEBUG" == true ]] && echo "[DEBUG] Sent: $channel [$severity]" >&2
            return 0
            ;;
        401|403)
            echo "ERROR: Authentication failed (HTTP $http_code)" >&2
            exit 3
            ;;
        000)
            echo "ERROR: Cannot connect to API: $url" >&2
            exit 2
            ;;
        *)
            echo "ERROR: API request failed (HTTP $http_code)" >&2
            exit 2
            ;;
    esac
}

# Main processing loop
main() {
    # Load configuration
    load_config

    # Parse command line arguments
    parse_args "$@"

    # Build API URL
    if [[ -n "$HOST_PORT" ]]; then
        # Explicit host:port provided
        if [[ "$HOST_PORT" =~ ^https?:// ]]; then
            API_URL="$HOST_PORT"
        else
            API_URL="http://$HOST_PORT"
        fi
    elif [[ -n "${TREE_SIGNAL_URL:-}" ]]; then
        # Use environment variable
        API_URL="$TREE_SIGNAL_URL"
    else
        # Use default
        API_URL="$DEFAULT_URL"
    fi

    # Get API key from environment if not set
    if [[ -n "${TREE_SIGNAL_API_KEY:-}" ]]; then
        API_KEY="$TREE_SIGNAL_API_KEY"
    fi

    # Set severity (default to info if not specified)
    if [[ -z "$SEVERITY" ]]; then
        SEVERITY="$DEFAULT_SEVERITY"
    fi
    SEVERITY=$(validate_severity "$SEVERITY")

    [[ "$QUIET" == false ]] && echo "[INFO] Reading from stdin, sending to $API_URL → $CHANNEL [$SEVERITY]" >&2

    # Handle SIGINT/SIGTERM gracefully
    trap 'echo "[INFO] Shutting down..." >&2; exit 0' SIGINT SIGTERM

    # Read from stdin line by line
    local line_count=0
    while IFS= read -r line; do
        # Skip empty lines
        [[ -z "$line" ]] && continue

        # Send message
        send_message "$CHANNEL" "$line" "$SEVERITY" "$API_URL"

        line_count=$((line_count + 1))
        [[ "$DEBUG" == true ]] && echo "[DEBUG] Processed $line_count lines" >&2
    done

    [[ "$QUIET" == false ]] && echo "[INFO] Processed $line_count messages" >&2
}

# Run main function
main "$@"
