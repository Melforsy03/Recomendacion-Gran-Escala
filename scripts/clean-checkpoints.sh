#!/bin/bash
###############################################################################
# Script: clean-checkpoints.sh
# Descripción: Limpia checkpoints corruptos de HDFS para todos los procesos
# Uso: ./scripts/clean-checkpoints.sh [OPCIÓN]
#      OPCIÓN: all | streaming | latent | batch
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Opción (default: all)
OPTION="${1:-all}"

# Banner
clear
echo "==============================================================================="
echo -e "${BLUE}🧹 LIMPIEZA DE CHECKPOINTS HDFS${NC}"
echo "==============================================================================="
echo -e "📍 Proyecto: $(basename "$PROJECT_ROOT")"
echo -e "🎯 Modo: ${CYAN}${OPTION}${NC}"
echo "==============================================================================="
echo ""

# ==========================================
# Verificar que HDFS esté disponible
# ==========================================

echo -e "${YELLOW}🔍 Verificando HDFS...${NC}"
if ! docker ps | grep -q namenode; then
    echo -e "${RED}❌ Error: HDFS namenode no está corriendo${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta ./scripts/start-system.sh primero${NC}"
    exit 1
fi
echo -e "${GREEN}✅ HDFS disponible${NC}"
echo ""

# ==========================================
# Función para limpiar checkpoints
# ==========================================

clean_checkpoint() {
    local path=$1
    local description=$2
    
    echo -e "${YELLOW}🗑️  Limpiando: ${description}${NC}"
    echo -e "   📂 Ruta: ${path}"
    
    if docker exec namenode hadoop fs -test -d "$path" 2>/dev/null; then
        docker exec namenode hadoop fs -rm -r -f "$path" 2>/dev/null
        echo -e "${GREEN}   ✅ Eliminado${NC}"
    else
        echo -e "${CYAN}   ℹ️  No existía${NC}"
    fi
    echo ""
}

# ==========================================
# Limpieza según opción
# ==========================================

case "$OPTION" in
    "streaming")
        echo "==============================================================================="
        echo -e "${BLUE}📡 LIMPIANDO CHECKPOINTS DE STREAMING PROCESSOR${NC}"
        echo "==============================================================================="
        echo ""

        clean_checkpoint "/checkpoints/ratings_stream/processor/raw" \
            "Raw ratings (escritura HDFS)"

        clean_checkpoint "/checkpoints/ratings_stream/processor/console_debug" \
            "Console debug output"

        clean_checkpoint "/checkpoints/ratings_stream/processor/tumbling" \
            "Agregaciones tumbling window (HDFS)"

        clean_checkpoint "/checkpoints/ratings_stream/processor/sliding" \
            "Agregaciones sliding window (HDFS)"

        # Limpieza de checkpoints de agregaciones (posibles .delta corruptos)
        clean_checkpoint "/checkpoints/ratings_stream/processor/agg_sliding" \
            "Agregaciones sliding (state/offsets/commits)"

        clean_checkpoint "/checkpoints/ratings_stream/processor/agg_tumbling" \
            "Agregaciones tumbling (state/offsets/commits)"

        clean_checkpoint "/checkpoints/ratings_stream/processor/metrics_tumbling" \
            "Métricas tumbling (Kafka)"

        clean_checkpoint "/checkpoints/ratings_stream/processor/metrics_sliding" \
            "Métricas sliding (Kafka)"

        # Recrear estructura base
        echo -e "${YELLOW}📁 Recreando estructura base...${NC}"
        docker exec namenode hadoop fs -mkdir -p /checkpoints/ratings_stream/processor 2>/dev/null || true
        echo -e "${GREEN}✅ Estructura recreada${NC}"
        echo ""
        ;;

    "latent")
        echo "==============================================================================="
        echo -e "${BLUE}🎲 LIMPIANDO CHECKPOINTS DE LATENT GENERATOR${NC}"
        echo "==============================================================================="
        echo ""

        clean_checkpoint "/checkpoints/latent_ratings" \
            "Generador de ratings sintéticos"

        # Recrear estructura base
        echo -e "${YELLOW}📁 Recreando estructura base...${NC}"
        docker exec namenode hadoop fs -mkdir -p /checkpoints 2>/dev/null || true
        echo -e "${GREEN}✅ Estructura recreada${NC}"
        echo ""
        ;;

    "batch")
        echo "==============================================================================="
        echo -e "${BLUE}📊 LIMPIANDO CHECKPOINTS DE BATCH ANALYTICS${NC}"
        echo "==============================================================================="
        echo ""

        clean_checkpoint "/checkpoints/batch_analytics" \
            "Análisis batch sobre streaming"

        # Recrear estructura base
        echo -e "${YELLOW}📁 Recreando estructura base...${NC}"
        docker exec namenode hadoop fs -mkdir -p /checkpoints 2>/dev/null || true
        echo -e "${GREEN}✅ Estructura recreada${NC}"
        echo ""
        ;;

    "all")
        # Ejecutar las tres limpiezas en orden
        "$0" streaming
        "$0" latent
        "$0" batch
        ;;

    "help"|"-h"|"--help")
        echo -e "${BLUE}USO${NC}"
        echo "  $0 [OPCIÓN]"
        echo ""
        echo -e "${BLUE}OPCIONES${NC}"
        echo "  all        - Limpia todos los checkpoints (default)"
        echo "  streaming  - Solo streaming processor"
        echo "  latent     - Solo latent generator"
        echo "  batch      - Solo batch analytics"
        echo "  help       - Muestra esta ayuda"
        echo ""
        echo -e "${BLUE}EJEMPLOS${NC}"
        echo "  $0                    # Limpia todo"
        echo "  $0 streaming          # Solo streaming"
        echo "  $0 latent             # Solo generador"
        echo ""
        echo -e "${BLUE}CUÁNDO USAR${NC}"
        echo "  • FileAlreadyExistsException en checkpoints"
        echo "  • SparkConcurrentModificationException"
        echo "  • Checkpoint version mismatch"
        echo "  • Antes de reiniciar procesos streaming"
        echo ""
        exit 0
        ;;
    
    *)
        echo -e "${RED}❌ Opción no válida: ${OPTION}${NC}"
        echo ""
        echo "Uso: $0 [OPCIÓN]"
        echo ""
        echo "Opciones:"
        echo "  all        - Limpia todos los checkpoints (default)"
        echo "  streaming  - Solo streaming processor"
        echo "  latent     - Solo latent generator"
        echo "  batch      - Solo batch analytics"
        echo "  help       - Muestra ayuda detallada"
        echo ""
        echo "💡 Ejecuta: $0 help  para más información"
        echo ""
        exit 1
        ;;
esac

# ==========================================
# Resumen final
# ==========================================

echo "==============================================================================="
echo -e "${GREEN}✅ LIMPIEZA COMPLETADA${NC}"
echo "==============================================================================="
echo ""
echo -e "${BLUE}📋 Estructura de checkpoints actual:${NC}"
echo ""
docker exec namenode hadoop fs -ls -R /checkpoints 2>/dev/null || echo "   (vacío)"
echo ""
echo "==============================================================================="
echo -e "${CYAN}🚀 PRÓXIMOS PASOS${NC}"
echo "==============================================================================="
echo ""

case "$OPTION" in
    "streaming")
        echo "1️⃣  Iniciar generador de ratings:"
        echo "   ./scripts/run-latent-generator.sh 100"
        echo ""
        echo "2️⃣  Iniciar procesador de streaming:"
        echo "   ./scripts/run-streaming-processor.sh"
        ;;
    
    "latent")
        echo "1️⃣  Reiniciar generador de ratings:"
        echo "   ./scripts/run-latent-generator.sh 100"
        ;;
    
    "batch")
        echo "1️⃣  Ejecutar análisis batch:"
        echo "   ./scripts/run-batch-analytics.sh"
        ;;
    
    "all")
        echo "1️⃣  Iniciar sistema completo:"
        echo "   ./scripts/start-system.sh"
        echo ""
        echo "2️⃣  Generar ratings sintéticos:"
        echo "   ./scripts/run-latent-generator.sh 100"
        echo ""
        echo "3️⃣  Procesar streaming:"
        echo "   ./scripts/run-streaming-processor.sh"
        echo ""
        echo "4️⃣  Analizar datos batch:"
        echo "   ./scripts/run-batch-analytics.sh"
        ;;
esac

echo ""
echo "==============================================================================="
echo ""
