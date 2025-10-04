#!/bin/bash

echo "📋 MOSTRANDO LOGS DEL SISTEMA"
echo "============================="

echo ""
echo "🔍 Logs de Consumer (Métricas en tiempo real):"
echo "----------------------------------------------"
tail -20 consumer.log

echo ""
echo "🚀 Logs de Producer (Generación de datos):"
echo "-----------------------------------------"
tail -10 producer.log

echo ""
echo "📊 Para ver logs en tiempo real:"
echo "   tail -f consumer.log"
echo "   tail -f producer.log"
