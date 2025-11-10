#!/bin/bash
###############################################################################
# Script: spark-job-manager.sh
# Descripción: Gestor de jobs Spark con control de recursos y prioridades
# Uso: ./scripts/spark-job-manager.sh [list|kill|resources|fair-mode]
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

COMMAND="${1:-list}"

# ===========================================================================
# FUNCIONES
# ===========================================================================

function list_jobs() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}📋 APLICACIONES SPARK ACTIVAS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Obtener info de la API REST de Spark
    APPS=$(docker exec spark-master curl -s http://localhost:8080/json/ 2>/dev/null || echo '{"activeapps":[]}')
    
    ACTIVE_COUNT=$(echo "$APPS" | grep -o '"status":"RUNNING"' | wc -l)
    
    if [ "$ACTIVE_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}ℹ  No hay aplicaciones activas${NC}"
        echo ""
        return
    fi
    
    echo -e "${GREEN}Aplicaciones activas: $ACTIVE_COUNT${NC}"
    echo ""
    
    # Listar procesos spark-submit
    echo -e "${CYAN}Detalles:${NC}"
    docker exec spark-master ps aux | grep spark-submit | grep -v grep | awk '{
        print "  PID: " $2
        print "  CMD: " substr($0, index($0,$11))
        print "  ---"
    }' || echo -e "${YELLOW}  No se encontraron detalles${NC}"
    
    echo ""
    
    # Recursos usados
    echo -e "${CYAN}Recursos del Worker:${NC}"
    WORKER_MEM=$(docker exec spark-worker env | grep SPARK_WORKER_MEMORY | cut -d= -f2)
    WORKER_CORES=$(docker exec spark-worker env | grep SPARK_WORKER_CORES | cut -d= -f2)
    echo "  Total: ${WORKER_CORES} cores, ${WORKER_MEM} memoria"
    echo ""
}

function kill_job() {
    local APP_ID="$1"
    
    echo -e "${YELLOW}⚠️  Deteniendo aplicación $APP_ID...${NC}"
    
    # Obtener PID del proceso
    PIDS=$(docker exec spark-master ps aux | grep spark-submit | grep -v grep | awk '{print $2}')
    
    if [ -z "$PIDS" ]; then
        echo -e "${RED}❌ No hay aplicaciones para detener${NC}"
        return 1
    fi
    
    for PID in $PIDS; do
        echo -e "${YELLOW}   Deteniendo PID $PID...${NC}"
        docker exec spark-master kill -15 "$PID" 2>/dev/null || true
    done
    
    sleep 2
    
    # Force kill si es necesario
    REMAINING=$(docker exec spark-master ps aux | grep spark-submit | grep -v grep | wc -l)
    if [ "$REMAINING" -gt 0 ]; then
        echo -e "${YELLOW}   Forzando detención...${NC}"
        docker exec spark-master pkill -9 -f spark-submit || true
    fi
    
    echo -e "${GREEN}✅ Aplicaciones detenidas${NC}"
}

function kill_all_jobs() {
    echo -e "${YELLOW}⚠️  Deteniendo TODAS las aplicaciones Spark...${NC}"
    
    docker exec spark-master pkill -15 -f spark-submit 2>/dev/null || true
    sleep 3
    docker exec spark-master pkill -9 -f spark-submit 2>/dev/null || true
    
    echo -e "${GREEN}✅ Todas las aplicaciones detenidas${NC}"
}

function show_resources() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}💾 RECURSOS SPARK${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Configuración del worker
    echo -e "${CYAN}Worker Configuration:${NC}"
    docker exec spark-worker env | grep SPARK_WORKER | while read line; do
        echo "  $line"
    done
    echo ""
    
    # Uso actual Docker
    echo -e "${CYAN}Docker Stats:${NC}"
    docker stats --no-stream --format "  {{.Name}}: CPU={{.CPUPerc}} MEM={{.MemUsage}}" spark-master spark-worker
    echo ""
    
    # Aplicaciones activas
    ACTIVE=$(docker exec spark-master ps aux 2>/dev/null | grep spark-submit | grep -v grep | wc -l || echo "0")
    ACTIVE=$(echo "$ACTIVE" | tr -d '\n' | tr -d ' ' | head -c 1)
    [ -z "$ACTIVE" ] && ACTIVE=0
    echo -e "${CYAN}Aplicaciones Activas:${NC} $ACTIVE"
    echo ""
    
    # Recursos disponibles estimados
    WORKER_CORES=$(docker exec spark-worker env | grep SPARK_WORKER_CORES | cut -d= -f2)
    CORES_PER_APP=2
    AVAILABLE_SLOTS=$((WORKER_CORES / CORES_PER_APP))
    if [ "$ACTIVE" -gt 0 ] 2>/dev/null; then
        USED_SLOTS=$ACTIVE
    else
        USED_SLOTS=0
    fi
    FREE_SLOTS=$((AVAILABLE_SLOTS - USED_SLOTS))
    
    echo -e "${CYAN}Slots de Ejecución:${NC}"
    echo "  Total: $AVAILABLE_SLOTS jobs (con 2 cores cada uno)"
    echo "  Usados: $USED_SLOTS"
    echo "  Libres: $FREE_SLOTS"
    echo ""
}

function enable_fair_scheduling() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}⚙️  CONFIGURANDO FAIR SCHEDULING${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Crear directorio de configuración si no existe
    docker exec spark-master mkdir -p /opt/spark/conf 2>/dev/null || true
    
    # Crear archivo de configuración fair scheduling
    cat > /tmp/fairscheduler.xml <<'EOF'
<?xml version="1.0"?>
<allocations>
  <!-- Pool para streaming (prioridad alta, recursos garantizados) -->
  <pool name="streaming">
    <schedulingMode>FAIR</schedulingMode>
    <weight>2</weight>
    <minShare>1</minShare>
  </pool>
  
  <!-- Pool para batch (prioridad baja) -->
  <pool name="batch">
    <schedulingMode>FAIR</schedulingMode>
    <weight>1</weight>
    <minShare>1</minShare>
  </pool>
  
  <!-- Pool para generadores (prioridad baja) -->
  <pool name="generator">
    <schedulingMode>FAIR</schedulingMode>
    <weight>1</weight>
    <minShare>1</minShare>
  </pool>
  
  <!-- Pool default -->
  <pool name="default">
    <schedulingMode>FAIR</schedulingMode>
    <weight>1</weight>
    <minShare>1</minShare>
  </pool>
</allocations>
EOF
    
    # Copiar a spark-master
    docker cp /tmp/fairscheduler.xml spark-master:/opt/spark/conf/fairscheduler.xml
    
    echo -e "${GREEN}✅ Archivo fairscheduler.xml creado${NC}"
    echo ""
    echo -e "${YELLOW}📝 Configuración:${NC}"
    echo "  - Pool 'streaming': Prioridad alta, peso 2"
    echo "  - Pool 'batch': Prioridad media, peso 1"
    echo "  - Pool 'generator': Prioridad baja, peso 1"
    echo ""
    echo -e "${YELLOW}💡 Los scripts ya están configurados para usar Fair Scheduling${NC}"
    echo ""
}

function show_help() {
    echo -e "${CYAN}Uso: $0 [comando]${NC}"
    echo ""
    echo "Comandos disponibles:"
    echo "  list          - Lista aplicaciones Spark activas"
    echo "  kill-all      - Detiene todas las aplicaciones"
    echo "  resources     - Muestra recursos disponibles y uso"
    echo "  fair-mode     - Configura Fair Scheduling"
    echo "  help          - Muestra esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 list"
    echo "  $0 kill-all"
    echo "  $0 resources"
    echo ""
}

# ===========================================================================
# MAIN
# ===========================================================================

case "$COMMAND" in
    list)
        list_jobs
        ;;
    kill-all)
        kill_all_jobs
        ;;
    resources)
        show_resources
        ;;
    fair-mode)
        enable_fair_scheduling
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Comando desconocido: $COMMAND${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
