#!/bin/bash
set -e

echo "=========================================="
echo "Iniciando Sistema de Big Data"
echo "=========================================="
echo ""

# Directorio del script y raíz del repositorio (buscando docker-compose.yml)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
find_repo_root() {
  local dir="$SCRIPT_DIR"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/docker-compose.yml" ]]; then
      echo "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  echo "$SCRIPT_DIR"
}
ROOT_DIR="$(find_repo_root)"

# Verificar que Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo. Por favor inicia Docker primero."
    exit 1
fi

echo "✓ Docker está corriendo"
echo ""

# Detectar versión de Docker Compose
if command -v docker compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Error: Docker Compose no está instalado"
    exit 1
fi

echo "✓ docker-compose está instalado"
echo ""

# Detener servicios existentes si los hay
echo "Deteniendo servicios existentes (si los hay)..."
$DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" down 2>/dev/null || true

# # Limpiar volúmenes problemáticos de Kafka y Zookeeper para evitar inconsistencias
# echo "⚠️  Limpiando volúmenes de Kafka y Zookeeper para evitar conflictos de Cluster ID..."
# docker volume rm recomendacion-gran-escala_kafka_data 2>/dev/null || true
# docker volume rm recomendacion-gran-escala_zookeeper_data recomendacion-gran-escala_zookeeper_log 2>/dev/null || true

echo ""
echo "Iniciando servicios..."
$DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" up -d

echo ""
echo "Esperando que los servicios se inicialicen..."
echo "Esto puede tomar 1-2 minutos..."

# Esperar a que Zookeeper esté listo PRIMERO (crítico para Kafka)
echo -n "Esperando Zookeeper"
ZK_TIMEOUT=60
ZK_START=$(date +%s)
while true; do
    # Verificar que Zookeeper esté escuchando en el puerto 2181
    if docker exec zookeeper sh -c 'echo stat | nc localhost 2181 2>/dev/null' | grep -q "Mode:"; then
        echo " ✓"
        break
    fi
    # Fallback: verificar que el proceso esté corriendo
    if docker exec zookeeper pgrep -f QuorumPeerMain > /dev/null 2>&1; then
        echo " ✓ (proceso activo)"
        break
    fi
    NOW=$(date +%s)
    if (( NOW - ZK_START > ZK_TIMEOUT )); then
        echo " ✗ Timeout esperando Zookeeper"
        docker logs zookeeper --tail 50
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Dar tiempo a Zookeeper para estabilizarse completamente
sleep 5

# Esperar a que NameNode esté HEALTHY y salga de SafeMode (más fiable que sólo la UI)
echo -n "Esperando HDFS NameNode (HEALTHY)"
NAME_HEALTH_TIMEOUT=180 # seg
NAME_HEALTH_START=$(date +%s)
while true; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' namenode 2>/dev/null || echo "unknown")
    if [[ "$STATUS" == "healthy" ]]; then
        echo " ✓"
        break
    fi
    NOW=$(date +%s)
    if (( NOW - NAME_HEALTH_START > NAME_HEALTH_TIMEOUT )); then
        echo " ✗ Timeout esperando HEALTHY en NameNode"
        echo "Últimos logs de NameNode:" && docker logs --tail 100 namenode || true
        echo "Últimos logs de DataNode:" && docker logs --tail 100 datanode || true
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Esperar salida de SafeMode (el NameNode puede estar en SafeMode aunque la UI responda)
echo -n "Esperando salida de SafeMode en HDFS"
for i in {1..120}; do
    SM=$(docker exec namenode hdfs dfsadmin -safemode get 2>/dev/null || true)
    if echo "$SM" | grep -qi "OFF"; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
    if (( i % 30 == 0 )); then
        echo -e "\nEstado SafeMode: $SM"
    fi
done
SM=$(docker exec namenode hdfs dfsadmin -safemode get 2>/dev/null || true)
if ! echo "$SM" | grep -qi "OFF"; then
    echo -e "\n✗ HDFS sigue en SafeMode. Diagnóstico rápido:"
    docker exec namenode hdfs dfsadmin -report | tail -n +1 || true
    echo "Logs recientes de NameNode:" && docker logs --tail 100 namenode || true
    echo "Logs recientes de DataNode:" && docker logs --tail 100 datanode || true
    exit 1
fi

# Esperar a que YARN ResourceManager esté listo
echo -n "Esperando YARN ResourceManager (HEALTHY)"
RM_HEALTH_TIMEOUT=120
RM_HEALTH_START=$(date +%s)
while true; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' resourcemanager 2>/dev/null || echo "unknown")
    if [[ "$STATUS" == "healthy" ]]; then
        echo " ✓"
        break
    fi
    NOW=$(date +%s)
    if (( NOW - RM_HEALTH_START > RM_HEALTH_TIMEOUT )); then
        echo " ✗ Timeout esperando HEALTHY en ResourceManager"
        echo "Logs recientes de ResourceManager:" && docker logs --tail 100 resourcemanager || true
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Verificar que el cluster YARN está en estado STARTED (REST)
echo -n "Esperando estado STARTED en YARN"
YARN_TIMEOUT=180
YARN_START=$(date +%s)
while true; do
    if docker exec resourcemanager curl -fsS http://localhost:8088/ws/v1/cluster/info | grep -q '"state":"STARTED"'; then
        echo " ✓"
        break
    fi
    NOW=$(date +%s)
    if (( NOW - YARN_START > YARN_TIMEOUT )); then
        echo " ✗ Timeout esperando estado STARTED en YARN"
        echo "Últimos logs de ResourceManager:" && docker logs --tail 120 resourcemanager || true
        echo "Sondeo REST (dentro del contenedor):" && docker exec resourcemanager curl -sS http://localhost:8088/ws/v1/cluster/info || true
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Verificar al menos 1 NodeManager en estado RUNNING
echo -n "Esperando al menos 1 NodeManager RUNNING"
NM_TIMEOUT=180
NM_START=$(date +%s)
while true; do
     # Consultamos desde dentro del RM para evitar resets de red
    if docker exec resourcemanager curl -fsS 'http://localhost:8088/ws/v1/cluster/nodes?states=RUNNING' | grep -q '"state":"RUNNING"'; then
        echo " ✓"
        break
    fi
    NOW=$(date +%s)
    if (( NOW - NM_START > NM_TIMEOUT )); then
        echo " ✗ Timeout esperando NodeManager RUNNING"
        echo "Últimos logs de NodeManager:" && docker logs --tail 150 nodemanager || true
        echo "Últimos logs de ResourceManager:" && docker logs --tail 150 resourcemanager || true
        echo "Salida /ws/v1/cluster/nodes (RM):" && docker exec resourcemanager curl -sS 'http://localhost:8088/ws/v1/cluster/nodes?states=RUNNING' || true
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Esperar a que Spark Master esté listo (usa RPC primero para acelerar)
echo -n "Esperando Spark Master (RPC 7077)"
for i in {1..60}; do
    if command -v nc >/dev/null 2>&1; then
        if nc -z -w2 localhost 7077 2>/dev/null; then
            echo " ✓"
            break
        fi
    else
        # Fallback sin nc
        (echo > /dev/tcp/localhost/7077) >/dev/null 2>&1 && { echo " ✓"; break; }
    fi
    echo -n "."
    sleep 2
done

# Comprobar UI de Spark sin bloquear demasiado (opcional, max 20s)
echo -n "Esperando Spark Master UI (8080) (max 20s)"
SPARK_UI_TIMEOUT=20
SPARK_UI_START=$(date +%s)
while true; do
    # Chequeo desde dentro del contenedor usando /dev/tcp para no depender de curl/wget
    if docker exec spark-master bash -lc 'echo > /dev/tcp/localhost/8080' 2>/dev/null; then
        echo " ✓"
        break
    fi
    NOW=$(date +%s)
    if (( NOW - SPARK_UI_START > SPARK_UI_TIMEOUT )); then
        echo " (continuando sin UI)"
        break
    fi
    echo -n "."
    sleep 1
done

# Esperar a que Kafka esté listo (con reintentos si falla por nodo Zookeeper)
echo -n "Esperando Kafka"
KAFKA_TIMEOUT=120
KAFKA_START=$(date +%s)
KAFKA_READY=false

while true; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - KAFKA_START))
    
    # Verificar timeout
    if (( ELAPSED > KAFKA_TIMEOUT )); then
        echo ""
        echo "❌ Timeout esperando Kafka después de ${KAFKA_TIMEOUT}s"
        KAFKA_STATUS=$(docker inspect -f '{{.State.Status}}' kafka 2>/dev/null || echo "not_found")
        echo "Estado del contenedor: $KAFKA_STATUS"
        docker logs kafka --tail 50
        exit 1
    fi
    
    # Verificar estado del contenedor
    KAFKA_STATUS=$(docker inspect -f '{{.State.Status}}' kafka 2>/dev/null || echo "not_found")
    
    if [[ "$KAFKA_STATUS" == "exited" ]]; then
        # Kafka se cayó, verificar si es por problema de Zookeeper
        if docker logs kafka 2>&1 | grep -q "NodeExistsException"; then
            echo ""
            echo "⚠️  Detectado problema de nodo Zookeeper, reiniciando Kafka..."
            docker restart kafka
            sleep 5
            KAFKA_START=$(date +%s)  # Reiniciar temporizador
            echo -n "Esperando Kafka nuevamente"
        fi
    elif [[ "$KAFKA_STATUS" == "running" ]]; then
        # Método 1: Verificar que el puerto esté escuchando
        if command -v nc >/dev/null 2>&1; then
            if nc -z -w2 localhost 9092 2>/dev/null; then
                # Método 2: Verificar que los logs muestren que Kafka está listo
                if docker logs kafka 2>&1 | grep -q "started (kafka.server.KafkaServer)"; then
                    KAFKA_READY=true
                fi
            fi
        else
            # Fallback sin nc: verificar logs directamente
            if docker logs kafka 2>&1 | grep -q "started (kafka.server.KafkaServer)"; then
                KAFKA_READY=true
            fi
        fi
        
        # Método 3 (opcional): Intentar comando de API si los otros métodos pasaron
        if [[ "$KAFKA_READY" == "true" ]]; then
            # Dar un tiempo adicional para que la API esté completamente lista
            if (( ELAPSED > 10 )); then
                # Intentar verificación de API (con timeout corto para no bloquear)
                if timeout 3 docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1; then
                    echo " ✓"
                    break
                else
                    # Si falla la API pero los logs están OK, confiar en los logs
                    echo " ✓ (logs OK, API iniciando)"
                    break
                fi
            fi
        fi
    fi
    
    echo -n "."
    sleep 2
done

echo ""
echo "=========================================="
echo "✓ Sistema iniciado correctamente!"
echo "=========================================="
echo ""
echo "Interfaces Web Disponibles:"
echo "  - HDFS NameNode:        http://localhost:9870"
echo "  - YARN ResourceManager: http://localhost:8088"
echo "  - YARN NodeManager:     http://localhost:8042"
echo "  - Spark Master:         http://localhost:8080"
echo "  - Spark Worker:         http://localhost:8081"
echo ""
echo "Para verificar el estado de los servicios, ejecuta:"
echo "  $ROOT_DIR/tests/test-connectivity.sh"
echo ""
echo "Para ejecutar todos los tests de funcionalidad:"
echo "  $SCRIPT_DIR/run-all-tests.sh"
echo ""
echo "Para ver los logs de los servicios:"
echo "  $DOCKER_COMPOSE -f \"$ROOT_DIR/docker-compose.yml\" logs -f"
echo ""
