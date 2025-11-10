#!/bin/bash
###############################################################################
# Script: verify_fase9.sh
# Descripción: Verificación integral de la Fase 9 - Analytics Batch y Dashboard
# Uso: ./scripts/verify_fase9.sh
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0

# Funciones auxiliares
print_header() {
    echo ""
    echo "==============================================================================="
    echo -e "${BLUE}$1${NC}"
    echo "==============================================================================="
    echo ""
}

print_subheader() {
    echo ""
    echo -e "${CYAN}───────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}───────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ  $1${NC}"
}

# Banner
clear
echo "==============================================================================="
echo -e "${BLUE}🔍 VERIFICACIÓN INTEGRAL - FASE 9${NC}"
echo -e "${BLUE}   Analytics Batch + API + Dashboard${NC}"
echo "==============================================================================="
echo ""
echo -e "📅 Fecha: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ==========================================
# 1. Verificar Prerequisitos
# ==========================================

print_header "1️⃣  VERIFICACIÓN DE PREREQUISITOS"

# Docker
print_info "Verificando Docker..."
if command -v docker &> /dev/null; then
    print_success "Docker instalado: $(docker --version | cut -d' ' -f3 | tr -d ',')"
else
    print_error "Docker no está instalado"
    exit 1
fi

# Docker Compose
print_info "Verificando Docker Compose..."
if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose instalado: $(docker-compose --version | cut -d' ' -f4 | tr -d ',')"
else
    print_error "Docker Compose no está instalado"
    exit 1
fi

# ==========================================
# 2. Verificar Servicios Docker
# ==========================================

print_header "2️⃣  VERIFICACIÓN DE SERVICIOS DOCKER"

REQUIRED_SERVICES=(
    "namenode:HDFS NameNode"
    "datanode:HDFS DataNode"
    "spark-master:Spark Master"
    "spark-worker:Spark Worker"
    "kafka:Kafka Broker"
    "zookeeper:Zookeeper"
    "recs-api:API FastAPI"
)

for service in "${REQUIRED_SERVICES[@]}"; do
    IFS=':' read -r container_name service_desc <<< "$service"
    
    print_info "Verificando $service_desc ($container_name)..."
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        # Verificar que esté healthy o running
        status=$(docker inspect -f '{{.State.Status}}' "$container_name" 2>/dev/null || echo "unknown")
        health=$(docker inspect -f '{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
        
        if [[ "$status" == "running" ]]; then
            if [[ "$health" == "healthy" ]] || [[ "$health" == "none" ]]; then
                print_success "$service_desc está corriendo"
            else
                print_warning "$service_desc está corriendo pero health=$health"
            fi
        else
            print_error "$service_desc tiene status=$status"
        fi
    else
        print_error "$service_desc no está corriendo"
    fi
done

# Verificar Dashboard (puede no estar deployado aún)
print_info "Verificando Dashboard (opcional)..."
if docker ps --format '{{.Names}}' | grep -q "^recs-dashboard$"; then
    print_success "Dashboard Streamlit está corriendo"
    DASHBOARD_RUNNING=true
else
    print_warning "Dashboard no está corriendo (se puede iniciar con docker-compose up dashboard)"
    DASHBOARD_RUNNING=false
fi

# ==========================================
# 3. Verificar Datos de Streaming
# ==========================================

print_header "3️⃣  VERIFICACIÓN DE DATOS DE STREAMING"

print_info "Verificando directorio de ratings raw..."
if docker exec namenode hadoop fs -test -d /streams/ratings/raw 2>/dev/null; then
    count=$(docker exec namenode hadoop fs -count /streams/ratings/raw 2>/dev/null | awk '{print $2}')
    print_success "Directorio /streams/ratings/raw existe con $count subdirectorios"
else
    print_error "No existe /streams/ratings/raw"
    print_warning "Ejecuta: ./scripts/run-latent-generator.sh y ./scripts/run-streaming-processor.sh"
fi

print_info "Verificando directorio de ratings agregados..."
if docker exec namenode hadoop fs -test -d /streams/ratings/agg 2>/dev/null; then
    print_success "Directorio /streams/ratings/agg existe"
else
    print_error "No existe /streams/ratings/agg"
fi

# ==========================================
# 4. Verificar Análisis Batch
# ==========================================

print_header "4️⃣  VERIFICACIÓN DE ANÁLISIS BATCH"

print_subheader "Outputs de Analytics"

ANALYTICS_PATHS=(
    "/outputs/analytics/distributions/global:Distribución Global"
    "/outputs/analytics/distributions/by_genre:Distribución por Género"
    "/outputs/analytics/distributions/summary_stats:Estadísticas Resumen"
    "/outputs/analytics/topn/hourly:Top-N por Hora"
    "/outputs/analytics/topn/daily:Top-N por Día"
    "/outputs/analytics/trending/trending_movies:Películas Trending"
)

ANALYTICS_COMPLETE=true

for path_desc in "${ANALYTICS_PATHS[@]}"; do
    IFS=':' read -r hdfs_path desc <<< "$path_desc"
    
    print_info "Verificando $desc ($hdfs_path)..."
    
    if docker exec namenode hadoop fs -test -d "$hdfs_path" 2>/dev/null; then
        # Verificar que tenga archivos
        file_count=$(docker exec namenode hadoop fs -ls "$hdfs_path" 2>/dev/null | grep -c "\.parquet" || echo "0")
        
        if [[ "$file_count" -gt 0 ]]; then
            print_success "$desc existe con $file_count archivo(s) Parquet"
        else
            print_warning "$desc existe pero no tiene archivos Parquet"
            ANALYTICS_COMPLETE=false
        fi
    else
        print_error "$desc no existe"
        ANALYTICS_COMPLETE=false
    fi
done

if [[ "$ANALYTICS_COMPLETE" == false ]]; then
    print_warning "Análisis batch incompleto. Ejecuta: ./scripts/run-batch-analytics.sh"
fi

# ==========================================
# 5. Verificar Topic Kafka
# ==========================================

print_header "5️⃣  VERIFICACIÓN DE TOPICS KAFKA"

print_info "Listando topics de Kafka..."
topics=$(docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null || echo "")

if echo "$topics" | grep -q "^ratings$"; then
    print_success "Topic 'ratings' existe"
else
    print_error "Topic 'ratings' no existe"
fi

if echo "$topics" | grep -q "^metrics$"; then
    print_success "Topic 'metrics' existe"
    
    # Verificar mensajes en metrics
    print_info "Verificando mensajes en topic 'metrics'..."
    msg_count=$(docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
        --broker-list localhost:9092 \
        --topic metrics 2>/dev/null | awk -F: '{sum += $3} END {print sum}' || echo "0")
    
    if [[ "$msg_count" -gt 0 ]]; then
        print_success "Topic 'metrics' tiene $msg_count mensaje(s)"
    else
        print_warning "Topic 'metrics' existe pero no tiene mensajes"
    fi
else
    print_error "Topic 'metrics' no existe"
fi

# ==========================================
# 6. Verificar API
# ==========================================

print_header "6️⃣  VERIFICACIÓN DE API REST"

API_URL="http://localhost:8000"

print_info "Verificando health de la API..."
if health_response=$(curl -s -f "$API_URL/metrics/health" 2>/dev/null); then
    status=$(echo "$health_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [[ "$status" == "healthy" ]]; then
        print_success "API está healthy"
    elif [[ "$status" == "no_data" ]]; then
        print_warning "API está conectada pero sin datos de streaming"
    else
        print_error "API respondió con status=$status"
    fi
else
    print_error "API no responde en $API_URL/metrics/health"
fi

# Verificar endpoints
ENDPOINTS=(
    "/metrics/summary:Resumen de Métricas"
    "/metrics/topn?limit=10:Top-N Películas"
    "/metrics/genres:Métricas por Género"
    "/metrics/history?limit=10:Historial"
)

for endpoint_desc in "${ENDPOINTS[@]}"; do
    IFS=':' read -r endpoint desc <<< "$endpoint_desc"
    
    print_info "Verificando endpoint $desc..."
    
    if response=$(curl -s -f "$API_URL$endpoint" 2>/dev/null); then
        # Verificar que sea JSON válido
        if echo "$response" | jq . &>/dev/null; then
            print_success "Endpoint $endpoint responde con JSON válido"
        else
            print_warning "Endpoint $endpoint responde pero no es JSON válido"
        fi
    else
        print_error "Endpoint $endpoint no responde"
    fi
    
    sleep 0.5
done

# ==========================================
# 7. Verificar SSE
# ==========================================

print_header "7️⃣  VERIFICACIÓN DE SERVER-SENT EVENTS (SSE)"

print_info "Probando conexión SSE (timeout 5s)..."

if sse_test=$(timeout 5s curl -s -N "$API_URL/metrics/stream" 2>/dev/null | head -n 5); then
    # Verificar que el stream comience con "data:"
    if echo "$sse_test" | grep -q "^data:"; then
        print_success "SSE endpoint funciona correctamente"
        echo ""
        print_info "Primeras líneas del stream:"
        echo "$sse_test" | head -n 3
    else
        print_warning "SSE endpoint responde pero formato inesperado"
    fi
else
    print_error "SSE endpoint no responde o timeout"
fi

# ==========================================
# 8. Verificar Dashboard
# ==========================================

print_header "8️⃣  VERIFICACIÓN DE DASHBOARD STREAMLIT"

if [[ "$DASHBOARD_RUNNING" == true ]]; then
    DASHBOARD_URL="http://localhost:8501"
    
    print_info "Verificando acceso al dashboard..."
    
    # Streamlit health endpoint
    if curl -s -f "$DASHBOARD_URL/_stcore/health" &>/dev/null; then
        print_success "Dashboard Streamlit está accesible en $DASHBOARD_URL"
    else
        print_warning "Dashboard está corriendo pero health endpoint no responde"
    fi
    
    # Verificar página principal
    print_info "Verificando página principal del dashboard..."
    if curl -s -f "$DASHBOARD_URL" &>/dev/null; then
        print_success "Página principal del dashboard responde"
    else
        print_error "Página principal del dashboard no responde"
    fi
else
    print_warning "Dashboard no está corriendo. Para iniciarlo:"
    echo ""
    echo "  docker-compose up -d dashboard"
    echo ""
fi

# ==========================================
# 9. Resumen de Verificación
# ==========================================

print_header "📊 RESUMEN DE VERIFICACIÓN"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

echo ""
echo "  Total de pruebas: $TOTAL_TESTS"
echo -e "  ${GREEN}✅ Pasadas: $TESTS_PASSED${NC}"
echo -e "  ${RED}❌ Fallidas: $TESTS_FAILED${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo "==============================================================================="
    echo -e "${GREEN}🎉 VERIFICACIÓN COMPLETADA EXITOSAMENTE${NC}"
    echo "==============================================================================="
    echo ""
    echo -e "${BLUE}✨ Fase 9 - Analytics Batch y Dashboard - OPERACIONAL${NC}"
    echo ""
    echo "Accesos:"
    echo ""
    echo "  📊 Dashboard:     http://localhost:8501"
    echo "  🔌 API REST:      http://localhost:8000/docs"
    echo "  📡 SSE Stream:    http://localhost:8000/metrics/stream"
    echo "  🎯 Spark UI:      http://localhost:8080"
    echo "  📁 HDFS UI:       http://localhost:9870"
    echo ""
    echo "Próximos pasos:"
    echo ""
    echo "  1. Generar ratings sintéticos:"
    echo "     ./scripts/run-latent-generator.sh 100"
    echo ""
    echo "  2. Procesar streaming:"
    echo "     ./scripts/run-streaming-processor.sh"
    echo ""
    echo "  3. Ejecutar análisis batch:"
    echo "     ./scripts/run-batch-analytics.sh"
    echo ""
    echo "  4. Ver dashboard:"
    echo "     http://localhost:8501"
    echo ""
    exit 0
else
    echo "==============================================================================="
    echo -e "${YELLOW}⚠️  VERIFICACIÓN COMPLETADA CON ADVERTENCIAS${NC}"
    echo "==============================================================================="
    echo ""
    echo -e "${YELLOW}Algunos componentes requieren atención.${NC}"
    echo ""
    echo "Acciones recomendadas:"
    echo ""
    
    if [[ "$ANALYTICS_COMPLETE" == false ]]; then
        echo "  • Ejecutar análisis batch:"
        echo "    ./scripts/run-batch-analytics.sh"
        echo ""
    fi
    
    if [[ "$DASHBOARD_RUNNING" == false ]]; then
        echo "  • Iniciar dashboard:"
        echo "    docker-compose up -d dashboard"
        echo ""
    fi
    
    echo "  • Revisar logs de servicios fallidos:"
    echo "    docker-compose logs -f [servicio]"
    echo ""
    exit 1
fi
