#!/bin/bash
###############################################################################
# Simula tráfico HTTP al sistema de recomendación
# Uso:
#   ./scripts/simulate-traffic.sh                    # usa valores por defecto
#   ./scripts/simulate-traffic.sh 50 300             # 50 req/s durante 300s
#   ./scripts/simulate-traffic.sh --rate 10 --duration 30
#
# Requiere: Python 3 con dependencias (aiohttp) instaladas
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TRAFFIC_SCRIPT="$PROJECT_ROOT/scripts/simulate_traffic.py"

# Valores por defecto
DEFAULT_RATE=10
DEFAULT_DURATION=30

# Determinar el ejecutable de Python a usar
if [[ -f "$PROJECT_ROOT/.venv/bin/python" ]]; then
    PYTHON_CMD="$PROJECT_ROOT/.venv/bin/python"
elif [[ -n "${VIRTUAL_ENV:-}" ]] && [[ -f "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON_CMD="${VIRTUAL_ENV}/bin/python"
else
    PYTHON_CMD="python3"
fi

# Verificar que existe el script
if [[ ! -f "$TRAFFIC_SCRIPT" ]]; then
    echo -e "${RED}❌ No se encontró el script de simulación en $TRAFFIC_SCRIPT${NC}"
    exit 1
fi

# Parsear argumentos
RATE=""
DURATION=""
API_URL=""

# Si los dos primeros argumentos son números, usarlos como rate y duration
if [[ $# -ge 2 ]] && [[ "$1" =~ ^[0-9]+$ ]] && [[ "$2" =~ ^[0-9]+$ ]]; then
    RATE="$1"
    DURATION="$2"
    shift 2
fi

# Parsear argumentos con flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --rate|-r)
            RATE="$2"
            shift 2
            ;;
        --duration|-d)
            DURATION="$2"
            shift 2
            ;;
        --api-url|--url)
            API_URL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Uso: $0 [OPCIONES]"
            echo ""
            echo "Opciones:"
            echo "  --rate, -r NUM         Peticiones por segundo (default: $DEFAULT_RATE)"
            echo "  --duration, -d NUM     Duración en segundos (default: $DEFAULT_DURATION)"
            echo "  --api-url URL          URL base de la API (default: http://localhost:8000)"
            echo "  --help, -h             Muestra esta ayuda"
            echo ""
            echo "Ejemplos:"
            echo "  $0                            # 10 req/s durante 30s"
            echo "  $0 50 300                     # 50 req/s durante 300s (5 min)"
            echo "  $0 --rate 10 --duration 30    # explícito"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Argumento desconocido: $1${NC}"
            echo "Usa --help para ver las opciones disponibles"
            exit 1
            ;;
    esac
done

# Usar valores por defecto si no se especificaron
RATE="${RATE:-$DEFAULT_RATE}"
DURATION="${DURATION:-$DEFAULT_DURATION}"

echo "===============================================================================" 
echo -e "${BLUE}🚀 Simulador de Tráfico HTTP${NC}"
echo "===============================================================================" 
echo -e "⚡ Rate:     ${YELLOW}${RATE}${NC} peticiones/segundo"
echo -e "⏱️  Duration: ${YELLOW}${DURATION}${NC} segundos"
if [[ -n "$API_URL" ]]; then
    echo -e "🌐 API URL:  ${YELLOW}${API_URL}${NC}"
else
    echo -e "🌐 API URL:  ${YELLOW}http://localhost:8000${NC} (default)"
fi
echo -e "🐍 Python:   ${YELLOW}${PYTHON_CMD}${NC}"
echo "===============================================================================" 

# Verificar que la API esté disponible
API_CHECK_URL="${API_URL:-http://localhost:8000}"
echo -e "${YELLOW}🔍 Verificando disponibilidad de la API...${NC}"
if ! curl -s -f "${API_CHECK_URL}/health" > /dev/null 2>&1 && \
   ! curl -s -f "${API_CHECK_URL}/" > /dev/null 2>&1; then
    echo -e "${RED}❌ La API no está disponible en ${API_CHECK_URL}${NC}"
    echo -e "${YELLOW}💡 Asegúrate de que la API esté corriendo:${NC}"
    echo "   docker ps | grep recsys-api"
    echo "   o inicia el sistema con: ./scripts/start-system.sh"
    exit 1
fi
echo -e "${GREEN}✅ API disponible${NC}"

# Verificar dependencias Python
echo -e "${YELLOW}🔍 Verificando dependencias Python (aiohttp)...${NC}"
if ! "$PYTHON_CMD" -c "import aiohttp" 2>/dev/null; then
    echo -e "${RED}❌ Falta la dependencia 'aiohttp'${NC}"
    echo -e "${YELLOW}📦 Instala con:${NC} $PYTHON_CMD -m pip install aiohttp"
    exit 1
fi
echo -e "${GREEN}✅ Dependencias disponibles${NC}"

# Limpieza al salir
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Deteniendo simulador de tráfico...${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${GREEN}▶️  Iniciando simulación (Ctrl+C para detener)...${NC}"
echo ""

# Construir comando
CMD=("$PYTHON_CMD" "$TRAFFIC_SCRIPT" "--rate" "$RATE" "--duration" "$DURATION")
if [[ -n "$API_URL" ]]; then
    CMD+=("--api-url" "$API_URL")
fi

# Ejecutar
"${CMD[@]}"

EXIT_CODE=$?
echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ Simulación completada correctamente${NC}"
    echo -e "${YELLOW}📊 Los logs se guardaron en: logs/${NC}"
else
    echo -e "${RED}❌ Simulación finalizada con errores (código: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
