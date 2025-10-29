#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 6: Creación de Topics Kafka y Esquema de Eventos
======================================================

Script para crear y verificar topics de Kafka para streaming de ratings.

Topics:
- ratings: Input de ratings en tiempo real
- metrics: Output de métricas de streaming

Esquema JSON ratings:
{
    "userId": int,
    "movieId": int,
    "rating": double,
    "timestamp": long
}

Uso:
    python create_kafka_topics.py
"""

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import sys
import time

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092']  # Dentro de red Docker
KAFKA_BOOTSTRAP_SERVERS_EXTERNAL = ['localhost:9093']  # Desde host

TOPICS_CONFIG = [
    {
        'name': 'ratings',
        'partitions': 3,
        'replication_factor': 1,
        'config': {
            'retention.ms': str(7 * 24 * 60 * 60 * 1000),  # 7 días
            'compression.type': 'lz4',
            'segment.bytes': str(100 * 1024 * 1024)  # 100 MB
        }
    },
    {
        'name': 'metrics',
        'partitions': 1,
        'replication_factor': 1,
        'config': {
            'retention.ms': str(30 * 24 * 60 * 60 * 1000),  # 30 días
            'compression.type': 'gzip',
            'cleanup.policy': 'delete'
        }
    }
]

# ============================================================================
# FUNCIONES
# ============================================================================

def create_admin_client(bootstrap_servers):
    """
    Crea cliente admin de Kafka con reintentos.
    
    Args:
        bootstrap_servers: Lista de servidores Kafka
        
    Returns:
        KafkaAdminClient o None si falla
    """
    max_retries = 5
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id='topic-creator',
                request_timeout_ms=10000,
                api_version=(2, 5, 0)
            )
            print(f"✅ Conectado a Kafka en {bootstrap_servers}")
            return admin_client
        except Exception as e:
            print(f"⚠️  Intento {attempt + 1}/{max_retries} - Error: {str(e)}")
            if attempt < max_retries - 1:
                print(f"   Reintentando en {retry_delay} segundos...")
                time.sleep(retry_delay)
            else:
                print(f"❌ No se pudo conectar a Kafka después de {max_retries} intentos")
                return None


def create_topics(admin_client, topics_config):
    """
    Crea topics de Kafka según configuración.
    
    Args:
        admin_client: KafkaAdminClient
        topics_config: Lista de configuraciones de topics
        
    Returns:
        dict con resultados de creación
    """
    print("\n📝 Creando topics de Kafka...")
    
    new_topics = []
    for topic_conf in topics_config:
        topic = NewTopic(
            name=topic_conf['name'],
            num_partitions=topic_conf['partitions'],
            replication_factor=topic_conf['replication_factor'],
            topic_configs=topic_conf.get('config', {})
        )
        new_topics.append(topic)
    
    results = {
        'created': [],
        'already_exists': [],
        'failed': []
    }
    
    try:
        # Crear topics
        create_result = admin_client.create_topics(
            new_topics=new_topics,
            validate_only=False
        )
        
        # Procesar resultados
        for topic_name, future in create_result.items():
            try:
                future.result()  # Bloquea hasta completar
                results['created'].append(topic_name)
                print(f"  ✅ Topic '{topic_name}' creado exitosamente")
            except TopicAlreadyExistsError:
                results['already_exists'].append(topic_name)
                print(f"  ℹ️  Topic '{topic_name}' ya existe")
            except Exception as e:
                results['failed'].append((topic_name, str(e)))
                print(f"  ❌ Error creando topic '{topic_name}': {str(e)}")
    
    except Exception as e:
        print(f"❌ Error general creando topics: {str(e)}")
        for topic_conf in topics_config:
            results['failed'].append((topic_conf['name'], str(e)))
    
    return results


def describe_topics(admin_client, topic_names):
    """
    Obtiene descripción detallada de topics.
    
    Args:
        admin_client: KafkaAdminClient
        topic_names: Lista de nombres de topics
    """
    print("\n📊 Descripción de topics creados:")
    
    try:
        # Obtener metadata de topics
        metadata = admin_client.describe_topics(topic_names)
        
        for topic_name, topic_metadata in metadata.items():
            print(f"\n  📁 Topic: {topic_name}")
            print(f"     Particiones: {len(topic_metadata['partitions'])}")
            
            for partition in topic_metadata['partitions']:
                print(f"       Partition {partition['partition']}: "
                      f"Leader={partition['leader']}, "
                      f"Replicas={partition['replicas']}, "
                      f"ISR={partition['isr']}")
    
    except Exception as e:
        print(f"❌ Error describiendo topics: {str(e)}")


def list_all_topics(admin_client):
    """
    Lista todos los topics disponibles en Kafka.
    
    Args:
        admin_client: KafkaAdminClient
        
    Returns:
        Lista de nombres de topics
    """
    try:
        topics = admin_client.list_topics()
        return topics
    except Exception as e:
        print(f"❌ Error listando topics: {str(e)}")
        return []


def display_summary(results, topics_config):
    """
    Muestra resumen de la creación de topics.
    
    Args:
        results: Resultados de create_topics
        topics_config: Configuración original de topics
    """
    print("\n" + "="*70)
    print("📋 RESUMEN DE CREACIÓN DE TOPICS")
    print("="*70)
    
    print(f"\n✅ Topics creados: {len(results['created'])}")
    for topic in results['created']:
        print(f"   - {topic}")
    
    if results['already_exists']:
        print(f"\nℹ️  Topics que ya existían: {len(results['already_exists'])}")
        for topic in results['already_exists']:
            print(f"   - {topic}")
    
    if results['failed']:
        print(f"\n❌ Topics que fallaron: {len(results['failed'])}")
        for topic, error in results['failed']:
            print(f"   - {topic}: {error}")
    
    print("\n📊 Configuración de topics:")
    for topic_conf in topics_config:
        print(f"\n  📁 {topic_conf['name']}:")
        print(f"     - Particiones: {topic_conf['partitions']}")
        print(f"     - Replication Factor: {topic_conf['replication_factor']}")
        print(f"     - Retention: {int(topic_conf['config'].get('retention.ms', 0)) / (24*60*60*1000)} días")
        print(f"     - Compression: {topic_conf['config'].get('compression.type', 'none')}")
    
    print("\n" + "="*70)


def validate_schema():
    """
    Valida y muestra el esquema JSON esperado para ratings.
    """
    print("\n📝 ESQUEMA JSON PARA TOPIC 'ratings':")
    print("="*70)
    
    schema = {
        "userId": "int - ID del usuario (1-138493)",
        "movieId": "int - ID de la película (1-131262)", 
        "rating": "double - Rating 0.5-5.0 en incrementos de 0.5",
        "timestamp": "long - Unix timestamp en milisegundos"
    }
    
    print("\n  Estructura:")
    for field, description in schema.items():
        print(f"    {field}: {description}")
    
    print("\n  Ejemplo válido:")
    example = {
        "userId": 123,
        "movieId": 456,
        "rating": 4.5,
        "timestamp": 1730232000000
    }
    
    import json
    print("    " + json.dumps(example, indent=4).replace('\n', '\n    '))
    
    print("\n  Validaciones:")
    print("    ✓ userId > 0")
    print("    ✓ movieId > 0")
    print("    ✓ rating ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0}")
    print("    ✓ timestamp > 0 (epoch millis)")
    
    print("\n" + "="*70)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Pipeline completo de creación de topics Kafka.
    """
    print("="*70)
    print("FASE 6: CREACIÓN DE TOPICS KAFKA")
    print("="*70)
    
    # Mostrar esquema esperado
    validate_schema()
    
    # Intentar conectar a Kafka (interno primero, luego externo)
    print("\n🔌 Conectando a Kafka...")
    
    admin_client = create_admin_client(KAFKA_BOOTSTRAP_SERVERS)
    
    if admin_client is None:
        print("\n⚠️  Intentando conexión externa (localhost:9093)...")
        admin_client = create_admin_client(KAFKA_BOOTSTRAP_SERVERS_EXTERNAL)
    
    if admin_client is None:
        print("\n❌ No se pudo conectar a Kafka. Verifica que el servicio esté corriendo.")
        print("   Ejecuta: docker-compose up -d zookeeper kafka")
        sys.exit(1)
    
    try:
        # Crear topics
        results = create_topics(admin_client, TOPICS_CONFIG)
        
        # Esperar un momento para que los topics se propaguen
        time.sleep(2)
        
        # Describir topics
        all_topic_names = [conf['name'] for conf in TOPICS_CONFIG]
        describe_topics(admin_client, all_topic_names)
        
        # Listar todos los topics
        print("\n📚 Todos los topics en Kafka:")
        all_topics = list_all_topics(admin_client)
        for topic in sorted(all_topics):
            marker = "✅" if topic in all_topic_names else "  "
            print(f"  {marker} {topic}")
        
        # Mostrar resumen
        display_summary(results, TOPICS_CONFIG)
        
        # Verificar éxito
        total_expected = len(TOPICS_CONFIG)
        total_ok = len(results['created']) + len(results['already_exists'])
        
        if total_ok == total_expected:
            print("\n✅ FASE 6 - CREACIÓN DE TOPICS COMPLETADA EXITOSAMENTE")
            print("\n🎯 Próximo paso: Ejecutar producer/consumer de prueba")
            print("   - Producer: python kafka_producer_hello.py")
            print("   - Consumer: python kafka_consumer_hello.py")
        else:
            print(f"\n⚠️  Solo {total_ok}/{total_expected} topics están disponibles")
            sys.exit(1)
    
    finally:
        admin_client.close()


if __name__ == "__main__":
    main()
