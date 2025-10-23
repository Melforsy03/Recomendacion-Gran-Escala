#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PRODUCER_FILE="$ROOT_DIR/movies/src/producer/kafka_events_producer.py"

if [[ ! -f "$PRODUCER_FILE" ]]; then
  echo "No se encuentra $PRODUCER_FILE" >&2
  exit 1
fi

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv-producer}"
PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

# Preparar entorno virtual para evitar PEP 668 (entornos gestionados por el sistema)
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creando entorno virtual en $VENV_DIR"
  if ! python3 -m venv "$VENV_DIR"; then
    echo "No se pudo crear el entorno virtual. Asegúrate de tener instalado 'python3-venv' (sudo apt install python3-venv)." >&2
    exit 1
  fi
fi

echo "Instalando dependencias en el venv (kafka-python)…"
"$PY" -m pip install --upgrade pip setuptools wheel >/dev/null
"$PIP" install -q kafka-python

echo "Lanzando productor de eventos… (Ctrl+C para detener)"
KAFKA_BOOTSTRAP=${KAFKA_BOOTSTRAP:-localhost:9093} \
EVENTS_TOPIC=${EVENTS_TOPIC:-events} \
"$PY" "$PRODUCER_FILE"
