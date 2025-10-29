#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 6: Kafka Consumer - Hello World
=====================================

Consumer de prueba que lee mensajes del topic 'ratings'.

Lee y valida eventos de ratings con el esquema:
{
    "userId": int,
    "movieId": int,
    "rating": double,
    "timestamp": long
}

Uso:
    python kafka_consumer_hello.py [--max-messages 10] [--timeout 30]
"""

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json
import argparse
from datetime import datetime
import signal
import sys

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092']
KAFKA_BOOTSTRAP_SERVERS_EXTERNAL = ['localhost:9093']
TOPIC_NAME = 'ratings'
GROUP_ID = 'ratings-consumer-hello-world'

# ============================================================================
# FUNCIONES
# ============================================================================

def create_consumer(bootstrap_servers, topic, group_id, auto_offset_reset='earliest'):
    """
    Crea consumer de Kafka.
    
    Args:
        bootstrap_servers: Lista de servidores Kafka
        topic: Nombre del topic a consumir
        group_id: ID del consumer group
        auto_offset_reset: 'earliest' o 'latest'
        
    Returns:
        KafkaConsumer o None si falla
    """
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=1000,  # Timeout para poll
            api_version=(2, 5, 0)
        )
        print(f"✅ Consumer conectado a Kafka en {bootstrap_servers}")
        print(f"   Topic: {topic}")
        print(f"   Group ID: {group_id}")
        print(f"   Auto offset reset: {auto_offset_reset}")
        return consumer
    except Exception as e:
        print(f"❌ Error creando consumer: {str(e)}")
        return None


def validate_rating_message(message):
    """
    Valida estructura del mensaje de rating.
    
    Args:
        message: dict con datos del mensaje
        
    Returns:
        (is_valid: bool, errors: list)
    """
    errors = []
    
    # Validar campos requeridos
    required_fields = ['userId', 'movieId', 'rating', 'timestamp']
    for field in required_fields:
        if field not in message:
            errors.append(f"Campo faltante: {field}")
    
    if errors:
        return False, errors
    
    # Validar tipos y rangos
    if not isinstance(message['userId'], int):
        errors.append("userId debe ser int")
    
    if not isinstance(message['movieId'], int):
        errors.append("movieId debe ser int")
    
    if not isinstance(message['rating'], (int, float)):
        errors.append("rating debe ser numérico")
    elif not (0.5 <= message['rating'] <= 5.0):
        errors.append("rating debe estar entre 0.5 y 5.0")
    
    if not isinstance(message['timestamp'], int):
        errors.append("timestamp debe ser long")
    
    return len(errors) == 0, errors


def process_message(record, stats):
    """
    Procesa un mensaje del consumer.
    
    Args:
        record: ConsumerRecord de Kafka
        stats: dict para acumular estadísticas
    """
    try:
        # Extraer información del record
        partition = record.partition
        offset = record.offset
        timestamp = record.timestamp
        key = record.key
        value = record.value
        
        # Validar mensaje
        is_valid, errors = validate_rating_message(value)
        
        if is_valid:
            stats['valid'] += 1
            status = "✅"
        else:
            stats['invalid'] += 1
            status = "❌"
            stats['errors'].append((offset, errors))
        
        # Mostrar mensaje
        print(f"\n{status} Mensaje recibido:")
        print(f"   Partition: {partition}, Offset: {offset}")
        print(f"   Key: {key}")
        print(f"   Timestamp: {datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Value: {json.dumps(value, indent=6)}")
        
        if not is_valid:
            print(f"   Errores de validación: {errors}")
        
        # Actualizar estadísticas
        stats['total'] += 1
        stats['last_offset'] = offset
        
        # Acumular ratings por estrella
        if is_valid:
            rating = value['rating']
            stats['ratings_distribution'][rating] = stats['ratings_distribution'].get(rating, 0) + 1
    
    except json.JSONDecodeError as e:
        print(f"❌ Error deserializando JSON: {str(e)}")
        stats['deserialize_errors'] += 1
    except Exception as e:
        print(f"❌ Error procesando mensaje: {str(e)}")
        stats['process_errors'] += 1


def consume_messages(consumer, max_messages=None, timeout_seconds=30):
    """
    Consume mensajes del topic con timeout.
    
    Args:
        consumer: KafkaConsumer
        max_messages: Número máximo de mensajes a consumir (None = ilimitado)
        timeout_seconds: Timeout en segundos de inactividad
        
    Returns:
        dict con estadísticas
    """
    print(f"\n📥 Consumiendo mensajes del topic '{TOPIC_NAME}'...")
    print("="*70)
    
    if max_messages:
        print(f"   Máximo de mensajes: {max_messages}")
    print(f"   Timeout de inactividad: {timeout_seconds} segundos")
    print(f"   Presiona Ctrl+C para detener")
    print("="*70)
    
    stats = {
        'total': 0,
        'valid': 0,
        'invalid': 0,
        'deserialize_errors': 0,
        'process_errors': 0,
        'last_offset': None,
        'errors': [],
        'ratings_distribution': {}
    }
    
    import time
    start_time = time.time()
    last_message_time = start_time
    
    try:
        while True:
            # Poll con timeout corto
            records = consumer.poll(timeout_ms=1000, max_records=10)
            
            if not records:
                # No hay mensajes nuevos
                elapsed_idle = time.time() - last_message_time
                
                if elapsed_idle > timeout_seconds:
                    print(f"\n⏱️  Timeout: {timeout_seconds}s sin mensajes nuevos")
                    break
                
                # Mostrar progreso cada 5 segundos
                if int(elapsed_idle) % 5 == 0 and elapsed_idle > 0:
                    print(f"   ... esperando mensajes ({int(elapsed_idle)}s) ...")
                
                continue
            
            # Procesar mensajes
            for topic_partition, messages in records.items():
                for message in messages:
                    process_message(message, stats)
                    last_message_time = time.time()
                    
                    # Verificar si alcanzamos el máximo
                    if max_messages and stats['total'] >= max_messages:
                        print(f"\n✅ Alcanzado máximo de {max_messages} mensajes")
                        return stats
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Consumidor detenido por usuario (Ctrl+C)")
    
    finally:
        end_time = time.time()
        stats['duration'] = end_time - start_time
    
    return stats


def display_summary(stats):
    """
    Muestra resumen del consumo de mensajes.
    
    Args:
        stats: dict con estadísticas
    """
    print("\n" + "="*70)
    print("📊 RESUMEN DE CONSUMO")
    print("="*70)
    
    print(f"\n📈 Mensajes procesados:")
    print(f"   Total: {stats['total']}")
    print(f"   Válidos: {stats['valid']} ({100*stats['valid']/max(stats['total'],1):.1f}%)")
    print(f"   Inválidos: {stats['invalid']}")
    print(f"   Errores de deserialización: {stats['deserialize_errors']}")
    print(f"   Errores de procesamiento: {stats['process_errors']}")
    
    if stats['last_offset'] is not None:
        print(f"\n📍 Último offset consumido: {stats['last_offset']}")
    
    if stats['duration']:
        print(f"\n⏱️  Duración: {stats['duration']:.2f} segundos")
        if stats['total'] > 0:
            print(f"🚀 Throughput: {stats['total']/stats['duration']:.2f} mensajes/seg")
    
    # Distribución de ratings
    if stats['ratings_distribution']:
        print(f"\n⭐ Distribución de ratings:")
        for rating in sorted(stats['ratings_distribution'].keys()):
            count = stats['ratings_distribution'][rating]
            bar = '█' * min(50, count)
            print(f"   {rating:.1f}: {bar} ({count})")
    
    # Mostrar errores de validación
    if stats['errors']:
        print(f"\n❌ Errores de validación ({len(stats['errors'])}):")
        for offset, errors in stats['errors'][:5]:  # Mostrar primeros 5
            print(f"   Offset {offset}: {', '.join(errors)}")
        
        if len(stats['errors']) > 5:
            print(f"   ... y {len(stats['errors']) - 5} errores más")
    
    print("\n" + "="*70)


# ============================================================================
# SIGNAL HANDLING
# ============================================================================

consumer_instance = None

def signal_handler(sig, frame):
    """Manejador de señal para cierre limpio."""
    print('\n\n⚠️  Señal de interrupción recibida. Cerrando consumer...')
    if consumer_instance:
        consumer_instance.close()
    sys.exit(0)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Consumer Hello World - Lee ratings de Kafka.
    """
    global consumer_instance
    
    parser = argparse.ArgumentParser(
        description='Kafka Consumer - Hello World para ratings'
    )
    parser.add_argument(
        '--max-messages',
        type=int,
        default=None,
        help='Número máximo de mensajes a consumir (default: ilimitado)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout de inactividad en segundos (default: 30)'
    )
    parser.add_argument(
        '--reset',
        choices=['earliest', 'latest'],
        default='earliest',
        help='Auto offset reset (default: earliest)'
    )
    args = parser.parse_args()
    
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*70)
    print("KAFKA CONSUMER - HELLO WORLD")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Topic: {TOPIC_NAME}")
    print(f"Group ID: {GROUP_ID}")
    print("="*70)
    
    # Crear consumer
    print("\n🔌 Conectando a Kafka...")
    consumer = create_consumer(
        KAFKA_BOOTSTRAP_SERVERS,
        TOPIC_NAME,
        GROUP_ID,
        auto_offset_reset=args.reset
    )
    
    if consumer is None:
        print("⚠️  Intentando conexión externa...")
        consumer = create_consumer(
            KAFKA_BOOTSTRAP_SERVERS_EXTERNAL,
            TOPIC_NAME,
            GROUP_ID,
            auto_offset_reset=args.reset
        )
    
    if consumer is None:
        print("\n❌ No se pudo conectar a Kafka")
        print("   Verifica que Kafka esté corriendo:")
        print("   docker-compose up -d zookeeper kafka")
        return 1
    
    consumer_instance = consumer
    
    try:
        # Consumir mensajes
        stats = consume_messages(
            consumer,
            max_messages=args.max_messages,
            timeout_seconds=args.timeout
        )
        
        # Mostrar resumen
        display_summary(stats)
        
        if stats['total'] > 0:
            print("\n✅ CONSUMER HELLO WORLD COMPLETADO EXITOSAMENTE")
            return 0
        else:
            print("\n⚠️  No se consumieron mensajes")
            print("   Verifica que el producer haya enviado datos:")
            print("   python kafka_producer_hello.py --count 10")
            return 1
    
    finally:
        consumer.close()
        print("\n🔌 Consumer cerrado")


if __name__ == "__main__":
    exit(main())
