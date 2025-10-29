#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 6: Kafka Producer - Hello World
=====================================

Producer de prueba que envía mensajes de ratings al topic 'ratings'.

Genera eventos de ratings sintéticos siguiendo el esquema:
{
    "userId": int,
    "movieId": int,  
    "rating": double,
    "timestamp": long
}

Uso:
    python kafka_producer_hello.py [--count 10]
"""

from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import random
import time
import argparse
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092']
KAFKA_BOOTSTRAP_SERVERS_EXTERNAL = ['localhost:9093']
TOPIC_NAME = 'ratings'

# Rangos válidos según MovieLens
USER_ID_RANGE = (1, 138493)
MOVIE_ID_RANGE = (1, 27278)
VALID_RATINGS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

# ============================================================================
# FUNCIONES
# ============================================================================

def create_producer(bootstrap_servers):
    """
    Crea producer de Kafka con configuración optimizada.
    
    Args:
        bootstrap_servers: Lista de servidores Kafka
        
    Returns:
        KafkaProducer o None si falla
    """
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8') if k else None,
            acks='all',  # Esperar confirmación de todas las replicas
            retries=3,
            max_in_flight_requests_per_connection=5,
            compression_type='lz4',
            api_version=(2, 5, 0)
        )
        print(f"✅ Producer conectado a Kafka en {bootstrap_servers}")
        return producer
    except Exception as e:
        print(f"❌ Error creando producer: {str(e)}")
        return None


def generate_rating_event():
    """
    Genera un evento de rating sintético válido.
    
    Returns:
        dict con estructura de rating
    """
    event = {
        "userId": random.randint(*USER_ID_RANGE),
        "movieId": random.randint(*MOVIE_ID_RANGE),
        "rating": random.choice(VALID_RATINGS),
        "timestamp": int(time.time() * 1000)  # Unix timestamp en millis
    }
    return event


def validate_rating_event(event):
    """
    Valida que un evento de rating cumpla el esquema.
    
    Args:
        event: dict con datos del rating
        
    Returns:
        (is_valid: bool, errors: list)
    """
    errors = []
    
    # Validar campos requeridos
    required_fields = ['userId', 'movieId', 'rating', 'timestamp']
    for field in required_fields:
        if field not in event:
            errors.append(f"Campo requerido faltante: {field}")
    
    if errors:
        return False, errors
    
    # Validar tipos
    if not isinstance(event['userId'], int) or event['userId'] <= 0:
        errors.append("userId debe ser int > 0")
    
    if not isinstance(event['movieId'], int) or event['movieId'] <= 0:
        errors.append("movieId debe ser int > 0")
    
    if not isinstance(event['rating'], (int, float)):
        errors.append("rating debe ser numérico")
    elif event['rating'] not in VALID_RATINGS:
        errors.append(f"rating debe ser uno de {VALID_RATINGS}")
    
    if not isinstance(event['timestamp'], int) or event['timestamp'] <= 0:
        errors.append("timestamp debe ser long > 0")
    
    return len(errors) == 0, errors


def send_rating(producer, topic, event, use_key=True):
    """
    Envía un evento de rating a Kafka.
    
    Args:
        producer: KafkaProducer
        topic: Nombre del topic
        event: dict con datos del rating
        use_key: Si True, usa userId como key para particionamiento
        
    Returns:
        bool indicando éxito
    """
    # Validar evento
    is_valid, errors = validate_rating_event(event)
    if not is_valid:
        print(f"❌ Evento inválido: {errors}")
        return False
    
    try:
        # Key para particionamiento (userId)
        key = event['userId'] if use_key else None
        
        # Enviar de forma asíncrona
        future = producer.send(
            topic=topic,
            key=key,
            value=event
        )
        
        # Obtener metadata del mensaje enviado
        record_metadata = future.get(timeout=10)
        
        print(f"✅ Enviado - userId={event['userId']}, "
              f"movieId={event['movieId']}, "
              f"rating={event['rating']:.1f} | "
              f"Partition={record_metadata.partition}, "
              f"Offset={record_metadata.offset}")
        
        return True
    
    except KafkaError as e:
        print(f"❌ Error de Kafka: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error enviando mensaje: {str(e)}")
        return False


def send_batch_ratings(producer, topic, count=10, delay=0.5):
    """
    Envía un batch de ratings de prueba.
    
    Args:
        producer: KafkaProducer
        topic: Nombre del topic
        count: Número de mensajes a enviar
        delay: Delay en segundos entre mensajes
        
    Returns:
        (sent: int, failed: int)
    """
    print(f"\n📤 Enviando {count} ratings de prueba a topic '{topic}'...")
    print("="*70)
    
    sent = 0
    failed = 0
    
    for i in range(count):
        # Generar evento
        event = generate_rating_event()
        
        # Mostrar cada 10 o si es el primero/último
        if i == 0 or i == count - 1 or (i + 1) % 10 == 0:
            print(f"\n[{i+1}/{count}] Generado:")
            print(f"  {json.dumps(event, indent=2)}")
        
        # Enviar
        success = send_rating(producer, topic, event)
        
        if success:
            sent += 1
        else:
            failed += 1
        
        # Delay entre mensajes (excepto el último)
        if i < count - 1 and delay > 0:
            time.sleep(delay)
    
    # Flush para asegurar que todos los mensajes se envíen
    producer.flush()
    
    return sent, failed


def display_summary(sent, failed, total_time):
    """
    Muestra resumen del envío de mensajes.
    
    Args:
        sent: Número de mensajes enviados exitosamente
        failed: Número de mensajes fallidos
        total_time: Tiempo total en segundos
    """
    print("\n" + "="*70)
    print("📊 RESUMEN DE ENVÍO")
    print("="*70)
    print(f"\n✅ Mensajes enviados: {sent}")
    print(f"❌ Mensajes fallidos: {failed}")
    print(f"📈 Total: {sent + failed}")
    print(f"⏱️  Tiempo total: {total_time:.2f} segundos")
    
    if sent > 0:
        print(f"🚀 Throughput: {sent / total_time:.2f} mensajes/seg")
    
    success_rate = 100 * sent / (sent + failed) if (sent + failed) > 0 else 0
    print(f"✓  Tasa de éxito: {success_rate:.1f}%")
    
    print("\n" + "="*70)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Producer Hello World - Envía ratings de prueba a Kafka.
    """
    parser = argparse.ArgumentParser(
        description='Kafka Producer - Hello World para ratings'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=10,
        help='Número de mensajes a enviar (default: 10)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay entre mensajes en segundos (default: 0.5)'
    )
    args = parser.parse_args()
    
    print("="*70)
    print("KAFKA PRODUCER - HELLO WORLD")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Topic: {TOPIC_NAME}")
    print(f"Mensajes a enviar: {args.count}")
    print("="*70)
    
    # Crear producer
    print("\n🔌 Conectando a Kafka...")
    producer = create_producer(KAFKA_BOOTSTRAP_SERVERS)
    
    if producer is None:
        print("⚠️  Intentando conexión externa...")
        producer = create_producer(KAFKA_BOOTSTRAP_SERVERS_EXTERNAL)
    
    if producer is None:
        print("\n❌ No se pudo conectar a Kafka")
        print("   Verifica que Kafka esté corriendo:")
        print("   docker-compose up -d zookeeper kafka")
        return 1
    
    try:
        # Enviar ratings
        start_time = time.time()
        sent, failed = send_batch_ratings(
            producer, 
            TOPIC_NAME, 
            count=args.count,
            delay=args.delay
        )
        end_time = time.time()
        
        # Mostrar resumen
        display_summary(sent, failed, end_time - start_time)
        
        if failed == 0:
            print("\n✅ PRODUCER HELLO WORLD COMPLETADO EXITOSAMENTE")
            return 0
        else:
            print(f"\n⚠️  Completado con {failed} errores")
            return 1
    
    finally:
        producer.close()
        print("\n🔌 Producer cerrado")


if __name__ == "__main__":
    exit(main())
