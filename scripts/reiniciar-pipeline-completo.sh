#!/bin/bash
###############################################################################
# Script: reiniciar-pipeline-completo.sh
# Descripción: Limpia y prepara el sistema para generar datos frescos
# Uso: ./scripts/reiniciar-pipeline-completo.sh
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "==============================================================================="
echo -e "${BLUE}🔄 REINICIO COMPLETO DEL PIPELINE${NC}"
echo "==============================================================================="
echo ""

# 1. Detener jobs Spark
echo -e "${YELLOW}1️⃣ Deteniendo jobs Spark...${NC}"
if docker exec spark-master pkill -9 -f spark-submit 2>/dev/null; then
    echo -e "${GREEN}   ✅ Jobs detenidos${NC}"
else
    echo -e "${CYAN}   ℹ️  No había jobs corriendo${NC}"
fi
echo ""

# 2. Limpiar HDFS
echo -e "${YELLOW}2️⃣ Limpiando HDFS...${NC}"
docker exec namenode hadoop fs -rm -r -f \
  /checkpoints/ratings_stream \
  /checkpoints/latent_ratings \
  /streams/ratings \
  /checkpoints/batch_analytics 2>/dev/null && echo -e "${GREEN}   ✅ HDFS limpio${NC}" || echo -e "${CYAN}   ℹ️  Directorios no existían${NC}"
echo ""

# 3. Limpiar Kafka topics
echo -e "${YELLOW}3️⃣ Limpiando topics de Kafka...${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic ratings 2>/dev/null && echo -e "${GREEN}   ✅ Topic 'ratings' eliminado${NC}" || echo -e "${CYAN}   ℹ️  Topic 'ratings' no existía${NC}"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic metrics 2>/dev/null && echo -e "${GREEN}   ✅ Topic 'metrics' eliminado${NC}" || echo -e "${CYAN}   ℹ️  Topic 'metrics' no existía${NC}"

echo -e "${YELLOW}   ⏳ Esperando 5 segundos para que Kafka procese...${NC}"
sleep 5
echo ""

# 4. Recrear topics
echo -e "${YELLOW}4️⃣ Recreando topics de Kafka...${NC}"
docker exec kafka kafka-topics --create \
  --topic ratings \
  --bootstrap-server localhost:9092 \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=3600000 2>/dev/null && echo -e "${GREEN}   ✅ Topic 'ratings' creado${NC}"

docker exec kafka kafka-topics --create \
  --topic metrics \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=3600000 2>/dev/null && echo -e "${GREEN}   ✅ Topic 'metrics' creado${NC}" || echo -e "${CYAN}   ℹ️  Topic 'metrics' ya existía${NC}"
echo ""

# 5. Reiniciar API
echo -e "${YELLOW}5️⃣ Reiniciando API...${NC}"
docker-compose restart api >/dev/null 2>&1 && echo -e "${GREEN}   ✅ API reiniciada${NC}"
sleep 3
echo ""

# 6. Mostrar instrucciones
echo "==============================================================================="
echo -e "${GREEN}✅ SISTEMA PREPARADO${NC}"
echo "==============================================================================="
echo ""
echo -e "${BLUE}📋 PRÓXIMOS PASOS:${NC}"
echo ""
echo -e "${CYAN}Terminal 1:${NC} Generar datos frescos (1-2 minutos)"
echo -e "  ${YELLOW}\$ ./scripts/run-latent-generator.sh 100${NC}"
echo -e "  ${CYAN}💡 Dejar correr ~2 minutos, luego presionar Ctrl+C${NC}"
echo ""
echo -e "${CYAN}Terminal 2:${NC} Iniciar procesador de streaming (dejar corriendo)"
echo -e "  ${YELLOW}\$ ./scripts/run-streaming-processor.sh${NC}"
echo -e "  ${CYAN}💡 NO detener - debe seguir corriendo${NC}"
echo ""
echo -e "${CYAN}Terminal 3:${NC} Verificar métricas (después de 1 minuto)"
echo -e "  ${YELLOW}\$ docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic metrics --max-messages 3${NC}"
echo ""
echo -e "${CYAN}Navegador:${NC} Abrir dashboard"
echo -e "  ${YELLOW}http://localhost:8501${NC}"
echo ""
echo "==============================================================================="
echo -e "${BLUE}🎯 TIMELINE ESPERADO:${NC}"
echo "==============================================================================="
echo -e "  0:00 - ${GREEN}✅ Limpieza completa (ya hecho)${NC}"
echo -e "  0:00 - Iniciar generador (Terminal 1)"
echo -e "  2:00 - Detener generador (Ctrl+C)"
echo -e "  2:00 - Iniciar streaming processor (Terminal 2)"
echo -e "  3:00 - Ver primeras ventanas con datos"
echo -e "  3:30 - Abrir dashboard → ${GREEN}FUNCIONANDO!${NC}"
echo "==============================================================================="
echo ""
