"""
Productor de datos simulados para Kafka
Genera ratings aleatorios de usuarios para testing
"""
import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

def create_producer():
    """Crear productor de Kafka"""
    return KafkaProducer(
        bootstrap_servers=['localhost:9093'],
        value_serializer=lambda x: json.dumps(x).encode('utf-8')
    )

def generate_rating():
    """Generar un rating aleatorio"""
    users = [f"user{i}" for i in range(1, 11)]  # 10 usuarios
    items = [f"item{i}" for i in range(1, 21)]  # 20 items
    
    return {
        "user_id": random.choice(users),
        "item_id": random.choice(items),
        "rating": round(random.uniform(1.0, 5.0), 1),
        "timestamp": datetime.now().isoformat() + "Z"
    }

def main():
    print("=" * 50)
    print("Productor de Datos de Prueba para Kafka")
    print("=" * 50)
    print("\nConectando a Kafka...")
    
    producer = create_producer()
    topic = "ratings"
    
    print(f"✓ Conectado. Enviando datos al topic '{topic}'")
    print("\nPresiona Ctrl+C para detener...\n")
    
    try:
        count = 0
        while True:
            rating = generate_rating()
            producer.send(topic, value=rating)
            count += 1
            
            print(f"[{count}] Enviado: {rating}")
            
            # Enviar un rating cada 1-3 segundos
            time.sleep(random.uniform(1, 3))
            
    except KeyboardInterrupt:
        print("\n\n✓ Detenido por el usuario")
    finally:
        producer.close()
        print(f"Total de mensajes enviados: {count}")

if __name__ == "__main__":
    main()
