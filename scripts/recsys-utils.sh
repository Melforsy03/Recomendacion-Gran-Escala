#!/bin/bash
# Script de utilidades para operaciones HDFS y Kafka del sistema de recomendación
# Fase 1: Verificación completada ✅

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# ==========================================
# Comandos HDFS
# ==========================================

function hdfs_ls() {
    local path="${1:-/}"
    print_info "Listando HDFS: $path"
    docker exec namenode hdfs dfs -ls "$path"
}

function hdfs_mkdir() {
    local path="$1"
    if [ -z "$path" ]; then
        print_error "Uso: hdfs_mkdir <path>"
        return 1
    fi
    print_info "Creando directorio HDFS: $path"
    docker exec namenode hdfs dfs -mkdir -p "$path"
    print_success "Directorio creado"
}

function hdfs_put() {
    local local_path="$1"
    local hdfs_path="$2"
    if [ -z "$local_path" ] || [ -z "$hdfs_path" ]; then
        print_error "Uso: hdfs_put <archivo_local> <ruta_hdfs>"
        return 1
    fi
    print_info "Copiando $local_path → HDFS:$hdfs_path"
    # Copiar al contenedor primero
    docker cp "$local_path" namenode:/tmp/upload_temp
    # Luego mover a HDFS
    docker exec namenode hdfs dfs -put /tmp/upload_temp "$hdfs_path"
    docker exec namenode rm /tmp/upload_temp
    print_success "Archivo subido a HDFS"
}

function hdfs_du() {
    local path="${1:-/}"
    print_info "Uso de disco en HDFS: $path"
    docker exec namenode hdfs dfs -du -h "$path"
}

function hdfs_rm() {
    local path="$1"
    if [ -z "$path" ]; then
        print_error "Uso: hdfs_rm <path>"
        return 1
    fi
    print_info "Eliminando de HDFS: $path"
    docker exec namenode hdfs dfs -rm -r "$path"
    print_success "Eliminado de HDFS"
}

function hdfs_status() {
    print_header "Estado del Cluster HDFS"
    docker exec namenode hdfs dfsadmin -report
}

# ==========================================
# Comandos Kafka
# ==========================================

function kafka_topics() {
    print_header "Topics de Kafka"
    if ! docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null; then
        print_error "No se puede conectar a Kafka. Verifica que el servicio esté corriendo."
        print_info "Intenta: docker logs kafka --tail 50"
        return 1
    fi
}

function kafka_create_topic() {
    local topic="$1"
    local partitions="${2:-3}"
    local replication="${3:-1}"
    
    if [ -z "$topic" ]; then
        print_error "Uso: kafka_create_topic <nombre> [partitions] [replication]"
        return 1
    fi
    
    print_info "Creando topic: $topic (partitions=$partitions, replication=$replication)"
    docker exec kafka kafka-topics --create \
        --topic "$topic" \
        --bootstrap-server localhost:9092 \
        --partitions "$partitions" \
        --replication-factor "$replication" \
        --if-not-exists
    print_success "Topic creado o ya existe"
}

function kafka_describe_topic() {
    local topic="$1"
    if [ -z "$topic" ]; then
        print_error "Uso: kafka_describe_topic <nombre>"
        return 1
    fi
    print_info "Describiendo topic: $topic"
    docker exec kafka kafka-topics --describe \
        --topic "$topic" \
        --bootstrap-server localhost:9092
}

function kafka_delete_topic() {
    local topic="$1"
    if [ -z "$topic" ]; then
        print_error "Uso: kafka_delete_topic <nombre>"
        return 1
    fi
    print_info "Eliminando topic: $topic"
    docker exec kafka kafka-topics --delete \
        --topic "$topic" \
        --bootstrap-server localhost:9092
    print_success "Topic eliminado"
}

function kafka_consume() {
    local topic="$1"
    local max_messages="${2:-10}"
    
    if [ -z "$topic" ]; then
        print_error "Uso: kafka_consume <topic> [max_messages]"
        return 1
    fi
    
    print_info "Consumiendo últimos $max_messages mensajes de: $topic"
    docker exec kafka kafka-console-consumer \
        --bootstrap-server localhost:9092 \
        --topic "$topic" \
        --from-beginning \
        --max-messages "$max_messages"
}

function kafka_produce() {
    local topic="$1"
    if [ -z "$topic" ]; then
        print_error "Uso: kafka_produce <topic>"
        print_info "Luego escribe mensajes (uno por línea), Ctrl+D para terminar"
        return 1
    fi
    
    print_info "Produciendo mensajes a: $topic"
    print_info "Escribe mensajes (uno por línea), Ctrl+D para terminar"
    docker exec -i kafka kafka-console-producer \
        --bootstrap-server localhost:9092 \
        --topic "$topic"
}

# ==========================================
# Comandos Spark
# ==========================================

function spark_submit() {
    local script="$1"
    shift  # Resto de argumentos son para el script
    
    if [ -z "$script" ]; then
        print_error "Uso: spark_submit <script.py> [args...]"
        return 1
    fi
    
    if [ ! -f "$script" ]; then
        print_error "Script no encontrado: $script"
        return 1
    fi
    
    local script_name=$(basename "$script")
    print_info "Copiando script a spark-master: $script_name"
    docker cp "$script" spark-master:/tmp/"$script_name"
    
    print_header "Ejecutando Spark Job: $script_name"
    docker exec spark-master spark-submit \
        --master spark://spark-master:7077 \
        --conf spark.sql.shuffle.partitions=200 \
        /tmp/"$script_name" "$@"
}

function spark_submit_kafka() {
    local script="$1"
    shift
    
    if [ -z "$script" ]; then
        print_error "Uso: spark_submit_kafka <script.py> [args...]"
        return 1
    fi
    
    if [ ! -f "$script" ]; then
        print_error "Script no encontrado: $script"
        return 1
    fi
    
    local script_name=$(basename "$script")
    print_info "Copiando script a spark-master: $script_name"
    docker cp "$script" spark-master:/tmp/"$script_name"
    
    print_header "Ejecutando Spark Streaming Job: $script_name"
    docker exec spark-master spark-submit \
        --master spark://spark-master:7077 \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
        --conf spark.sql.shuffle.partitions=200 \
        --conf spark.streaming.backpressure.enabled=true \
        /tmp/"$script_name" "$@"
}

function spark_ui() {
    print_info "Abriendo Spark Master UI en navegador..."
    xdg-open http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || echo "Abre manualmente: http://localhost:8080"
}

# ==========================================
# Comandos de Sistema
# ==========================================

function system_status() {
    print_header "Estado del Sistema de Recomendación"
    
    echo ""
    echo "Contenedores Docker:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(namenode|datanode|resourcemanager|nodemanager|spark|kafka|zookeeper|recs-api)" || true
    
    echo ""
    print_info "HDFS Raíz:"
    hdfs_ls / 2>/dev/null || print_error "HDFS no accesible"
    
    echo ""
    print_info "Topics Kafka:"
    kafka_topics 2>/dev/null || print_error "Kafka no accesible"
    
    echo ""
    print_info "UIs disponibles:"
    echo "  - HDFS NameNode:        http://localhost:9870"
    echo "  - YARN ResourceManager: http://localhost:8088"
    echo "  - Spark Master:         http://localhost:8080"
    echo "  - Spark Worker:         http://localhost:8081"
    echo "  - API Métricas:         http://localhost:8000"
}

function open_uis() {
    print_info "Abriendo interfaces web del sistema..."
    xdg-open http://localhost:9870 2>/dev/null || true  # HDFS
    sleep 1
    xdg-open http://localhost:8088 2>/dev/null || true  # YARN
    sleep 1
    xdg-open http://localhost:8080 2>/dev/null || true  # Spark Master
    
    print_success "UIs abiertas (si xdg-open está disponible)"
    print_info "URLs disponibles:"
    echo "  http://localhost:9870 - HDFS NameNode"
    echo "  http://localhost:8088 - YARN ResourceManager"
    echo "  http://localhost:8080 - Spark Master"
    echo "  http://localhost:8081 - Spark Worker"
}

# ==========================================
# Menu Principal
# ==========================================

function show_help() {
    cat <<EOF
Sistema de Recomendación de Películas - Utilidades CLI

USO: $0 <comando> [argumentos]

COMANDOS HDFS:
  hdfs-ls [path]              Listar contenidos HDFS (default: /)
  hdfs-mkdir <path>           Crear directorio en HDFS
  hdfs-put <local> <hdfs>     Subir archivo a HDFS
  hdfs-du [path]              Mostrar uso de disco HDFS
  hdfs-rm <path>              Eliminar archivo/directorio HDFS
  hdfs-status                 Reporte del cluster HDFS

COMANDOS KAFKA:
  kafka-topics                Listar topics
  kafka-create <topic> [p] [r] Crear topic (p=partitions, r=replication)
  kafka-describe <topic>      Describir topic
  kafka-delete <topic>        Eliminar topic
  kafka-consume <topic> [n]   Consumir n mensajes (default: 10)
  kafka-produce <topic>       Producir mensajes interactivamente

COMANDOS SPARK:
  spark-submit <script> [args]        Ejecutar script PySpark
  spark-submit-kafka <script> [args]  Ejecutar con Kafka packages
  spark-ui                            Abrir Spark UI

COMANDOS SISTEMA:
  status                      Estado general del sistema
  open-uis                    Abrir todas las UIs web
  help                        Mostrar esta ayuda

EJEMPLOS:
  $0 hdfs-mkdir /data/movielens/csv
  $0 hdfs-put Dataset/movie.csv /data/movielens/csv/movie.csv
  $0 kafka-create ratings 6 1
  $0 kafka-consume ratings 20
  $0 spark-submit jobs/etl_movielens.py
  $0 status

EOF
}

# ==========================================
# Main
# ==========================================

case "${1:-}" in
    # HDFS
    hdfs-ls) hdfs_ls "${2:-/}" ;;
    hdfs-mkdir) hdfs_mkdir "$2" ;;
    hdfs-put) hdfs_put "$2" "$3" ;;
    hdfs-du) hdfs_du "${2:-/}" ;;
    hdfs-rm) hdfs_rm "$2" ;;
    hdfs-status) hdfs_status ;;
    
    # Kafka
    kafka-topics) kafka_topics ;;
    kafka-create) kafka_create_topic "$2" "${3:-3}" "${4:-1}" ;;
    kafka-describe) kafka_describe_topic "$2" ;;
    kafka-delete) kafka_delete_topic "$2" ;;
    kafka-consume) kafka_consume "$2" "${3:-10}" ;;
    kafka-produce) kafka_produce "$2" ;;
    
    # Spark
    spark-submit) spark_submit "${@:2}" ;;
    spark-submit-kafka) spark_submit_kafka "${@:2}" ;;
    spark-ui) spark_ui ;;
    
    # Sistema
    status) system_status ;;
    open-uis) open_uis ;;
    help|--help|-h) show_help ;;
    
    "")
        print_error "No se especificó comando"
        echo ""
        show_help
        exit 1
        ;;
    *)
        print_error "Comando desconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
