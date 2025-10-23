#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

FILE_SRC="$ROOT_DIR/movies/src/streaming/metrics_streaming.py"
DEST_PATH="/tmp/metrics_streaming.py"

if [[ ! -f "$FILE_SRC" ]]; then
  echo "No se encuentra $FILE_SRC" >&2
  exit 1
fi

echo "Copiando job de streaming a spark-master…"
docker cp "$FILE_SRC" spark-master:"$DEST_PATH"

echo "Ejecutando spark-submit…"
RETRIES=${RETRIES:-3}
REPOS="https://repo.maven.apache.org/maven2,https://repo1.maven.org/maven2,https://maven-central.storage-download.googleapis.com/maven2"

# Aumentar timeouts de red para descargas Ivy/Maven (dentro del contenedor)
SUBMIT_OPTS="-Dsun.net.client.defaultConnectTimeout=120000 -Dsun.net.client.defaultReadTimeout=900000"

clean_corrupt_cache() {
  echo "Limpiando artefactos corruptos de Ivy en spark-master (si existen)…"
  docker exec -u root spark-master bash -lc "\
    rm -f /root/.ivy2/jars/*hadoop-client-runtime* 2>/dev/null || true; \
    rm -rf /root/.ivy2/cache/org.apache.hadoop/hadoop-client-runtime 2>/dev/null || true"
}

attempt=1
while (( attempt <= RETRIES )); do
  echo "Intento $attempt/$RETRIES: lanzando spark-submit…"
  # En cada intento limpiamos un posible jar corrupto que haya quedado a tamaño 0
  clean_corrupt_cache

  if docker exec -u root -e SPARK_SUBMIT_OPTS="$SUBMIT_OPTS" spark-master \
    spark-submit \
      --master spark://spark-master:7077 \
      --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
      --repositories "$REPOS" \
      "$DEST_PATH"; then
    echo "spark-submit finalizado correctamente."
    exit 0
  fi

  echo "spark-submit falló en el intento $attempt. Reintentando…"
  sleep $((attempt * 5))
  ((attempt++))
done

echo "Error: spark-submit falló tras $RETRIES intentos." >&2
exit 1
