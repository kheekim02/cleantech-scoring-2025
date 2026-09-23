#!/usr/bin/env bash
# SGLang RadixAttention High-Throughput Serving Daemon
# Manages the SGLang OpenAI-compatible inference server on Spark GB10 (port 30000).

set -eo pipefail

VENV_PATH="/data/scraping/venv"
PYTHON_BIN="${VENV_PATH}/bin/python"
PORT=30000
HOST="0.0.0.0"
PID_FILE="/data/scraping/sglang.pid"
LOG_DIR="/data/scraping/logs"
LOG_FILE="${LOG_DIR}/sglang.log"
DEFAULT_MODEL="/home/jkim/.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659"
MODEL_PATH="${MODEL_PATH:-$DEFAULT_MODEL}"

export CUDA_HOME="/usr/local/cuda"
export PATH="/usr/local/cuda/bin:${VENV_PATH}/bin:${PATH}"

mkdir -p "${LOG_DIR}"

start() {
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        if kill -0 "${PID}" 2>/dev/null; then
            echo "SGLang server is already running (PID: ${PID}) on port ${PORT}"
            return 0
        else
            rm -f "${PID_FILE}"
        fi
    fi

    echo "Starting SGLang server on port ${PORT}..."
    echo "Model: ${MODEL_PATH}"
    echo "Log: ${LOG_FILE}"

    nohup "${PYTHON_BIN}" -m sglang.launch_server \
        --model-path "${MODEL_PATH}" \
        --host "${HOST}" \
        --port "${PORT}" \
        --mem-fraction-static 0.75 \
        --disable-cuda-graph \
        --trust-remote-code \
        > "${LOG_FILE}" 2>&1 &

    PID=$!
    echo "${PID}" > "${PID_FILE}"
    echo "SGLang process spawned with PID ${PID}. Waiting for health check..."

    for i in {1..120}; do
        if curl -s "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
            echo "SGLang server successfully initialized and healthy on port ${PORT}!"
            return 0
        fi
        if ! kill -0 "${PID}" 2>/dev/null; then
            echo "SGLang process crashed on startup. Check ${LOG_FILE}"
            cat "${LOG_FILE}" | tail -n 30
            rm -f "${PID_FILE}"
            return 1
        fi
        sleep 2
    done

    echo "Timeout waiting for SGLang health check. Process still starting or check log: ${LOG_FILE}"
    return 1
}

stop() {
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        echo "Stopping SGLang server (PID: ${PID})..."
        kill -15 "${PID}" 2>/dev/null || true
        for i in {1..15}; do
            if ! kill -0 "${PID}" 2>/dev/null; then
                rm -f "${PID_FILE}"
                echo "SGLang server stopped."
                return 0
            fi
            sleep 1
        done
        echo "Force killing SGLang server..."
        kill -9 "${PID}" 2>/dev/null || true
        rm -f "${PID_FILE}"
        echo "SGLang server force-stopped."
    else
        echo "No PID file found. Checking for any running launch_server processes..."
        pkill -f "sglang.launch_server" || true
    fi
}

status() {
    if [ -f "${PID_FILE}" ]; then
        PID=$(cat "${PID_FILE}")
        if kill -0 "${PID}" 2>/dev/null; then
            echo "SGLang server is running with PID ${PID}"
            curl -s "http://127.0.0.1:${PORT}/v1/models" || echo " (HTTP endpoint not responding)"
            return 0
        fi
    fi
    echo "SGLang server is not running."
    return 3
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    health)
        curl -i "http://127.0.0.1:${PORT}/health"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|health}"
        exit 1
        ;;
esac
