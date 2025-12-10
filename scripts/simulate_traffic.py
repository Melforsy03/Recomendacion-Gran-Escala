#!/usr/bin/env python3
"""
Simulador de Tráfico HTTP - Sistema de Recomendación
======================================================

Simula tráfico realista de peticiones HTTP al sistema de recomendación
para pruebas de carga, latencia y rendimiento.

Características:
- Distribución realista de usuarios (80% existentes, 20% nuevos)
- Rate configurable (req/s)
- Duración configurable
- Métricas de latencia (p50, p95, p99)
- Logs detallados con timestamps

Uso:
    python scripts/simulate_traffic.py --rate 50 --duration 300

Autor: Sistema de Recomendación a Gran Escala
Fecha: 8 de diciembre de 2025
"""

import argparse
import json
import time
import random
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
import statistics


# ==========================================
# Configuración
# ==========================================

class Config:
    """Configuración del simulador"""
    
    # API endpoint
    API_BASE_URL = "http://localhost:8000"
    
    # Distribución de usuarios
    EXISTING_USERS_RATIO = 0.8  # 80% usuarios existentes
    NEW_USERS_RATIO = 0.2        # 20% usuarios nuevos
    
    # Rango de IDs de usuarios existentes (basado en MovieLens)
    MIN_USER_ID = 1
    MAX_USER_ID = 270_000
    
    # Rango para usuarios "nuevos" (fuera del training set)
    NEW_USER_MIN = 300_000
    NEW_USER_MAX = 400_000
    
    # Configuración de peticiones
    DEFAULT_N_RECOMMENDATIONS = 10
    
    # Timeouts
    REQUEST_TIMEOUT = 30  # segundos
    
    # Logging
    LOG_DIR = Path("logs")
    
    # Métricas agregadas cada N segundos
    METRICS_INTERVAL = 10


# ==========================================
# Generador de Peticiones
# ==========================================

class RequestGenerator:
    """Genera peticiones HTTP realistas"""
    
    def __init__(self):
        self.config = Config()
    
    def generate_user_id(self) -> int:
        """Genera ID de usuario según distribución"""
        if random.random() < self.config.EXISTING_USERS_RATIO:
            # Usuario existente
            return random.randint(self.config.MIN_USER_ID, self.config.MAX_USER_ID)
        else:
            # Usuario nuevo (fallback)
            return random.randint(self.config.NEW_USER_MIN, self.config.NEW_USER_MAX)
    
    def generate_request(self) -> Dict:
        """Genera una petición"""
        user_id = self.generate_user_id()
        n = random.choice([5, 10, 20])  # Variación en número de recs
        
        return {
            "endpoint": f"/recommendations/recommend/{user_id}",
            "params": {"n": n},
            "user_id": user_id,
            "n": n
        }


# ==========================================
# Cliente HTTP Asíncrono
# ==========================================

class HTTPClient:
    """Cliente HTTP asíncrono para hacer peticiones"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Hace petición GET"""
        url = f"{self.base_url}{endpoint}"
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params=params) as response:
                    latency = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "latency": latency,
                            "status": response.status,
                            "data": data
                        }
                    else:
                        return {
                            "success": False,
                            "latency": latency,
                            "status": response.status,
                            "error": f"HTTP {response.status}"
                        }
        
        except asyncio.TimeoutError:
            latency = time.time() - start_time
            return {
                "success": False,
                "latency": latency,
                "status": 0,
                "error": "Timeout"
            }
        
        except Exception as e:
            latency = time.time() - start_time
            return {
                "success": False,
                "latency": latency,
                "status": 0,
                "error": str(e)
            }


# ==========================================
# Simulador de Tráfico
# ==========================================

class TrafficSimulator:
    """Simulador principal de tráfico"""
    
    def __init__(self, rate: float, duration: int):
        """
        Inicializa el simulador
        
        Args:
            rate: Peticiones por segundo
            duration: Duración en segundos
        """
        self.rate = rate
        self.duration = duration
        self.interval = 1.0 / rate  # Intervalo entre peticiones
        
        self.generator = RequestGenerator()
        self.client = HTTPClient(Config.API_BASE_URL)
        
        # Métricas
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "latencies": [],
            "errors": defaultdict(int),
            "requests_per_second": [],
            "start_time": None,
            "end_time": None
        }
        
        # Logs
        self.log_file = None
    
    def setup_logging(self):
        """Configura archivo de logs"""
        Config.LOG_DIR.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"traffic_simulation_{timestamp}.jsonl"
        self.log_file = Config.LOG_DIR / log_filename
        
        print(f"📝 Logs: {self.log_file}")
    
    def log_request(self, request: Dict, response: Dict):
        """Registra una petición en el log"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request": request,
            "response": {
                "success": response["success"],
                "latency": response["latency"],
                "status": response["status"]
            }
        }
        
        if not response["success"]:
            log_entry["response"]["error"] = response["error"]
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    async def make_request(self):
        """Hace una petición"""
        request = self.generator.generate_request()
        response = await self.client.get(request["endpoint"], request["params"])
        
        # Actualizar métricas
        self.metrics["total_requests"] += 1
        self.metrics["latencies"].append(response["latency"])
        
        if response["success"]:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
            self.metrics["errors"][response["error"]] += 1
        
        # Registrar en log
        self.log_request(request, response)
        
        return response
    
    def print_progress(self, elapsed: float):
        """Imprime progreso actual"""
        progress_pct = (elapsed / self.duration) * 100
        
        # Calcular métricas actuales
        if len(self.metrics["latencies"]) > 0:
            latencies = self.metrics["latencies"][-100:]  # Últimas 100
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else avg_latency
        else:
            avg_latency = 0
            p95_latency = 0
        
        success_rate = (self.metrics["successful_requests"] / self.metrics["total_requests"] * 100) if self.metrics["total_requests"] > 0 else 0
        
        print(f"\r[{progress_pct:5.1f}%] "
              f"Requests: {self.metrics['total_requests']} | "
              f"Success: {success_rate:.1f}% | "
              f"Avg Latency: {avg_latency*1000:.0f}ms | "
              f"P95: {p95_latency*1000:.0f}ms",
              end='', flush=True)
    
    def save_metrics(self):
        """Guarda métricas finales"""
        # Calcular estadísticas
        latencies = self.metrics["latencies"]
        
        if len(latencies) > 0:
            sorted_latencies = sorted(latencies)
            
            metrics_summary = {
                "configuration": {
                    "rate": self.rate,
                    "duration": self.duration,
                    "api_base_url": Config.API_BASE_URL
                },
                "execution": {
                    "start_time": self.metrics["start_time"].isoformat(),
                    "end_time": self.metrics["end_time"].isoformat(),
                    "actual_duration": (self.metrics["end_time"] - self.metrics["start_time"]).total_seconds()
                },
                "requests": {
                    "total": self.metrics["total_requests"],
                    "successful": self.metrics["successful_requests"],
                    "failed": self.metrics["failed_requests"],
                    "success_rate": self.metrics["successful_requests"] / self.metrics["total_requests"] * 100,
                    "actual_rate": self.metrics["total_requests"] / (self.metrics["end_time"] - self.metrics["start_time"]).total_seconds()
                },
                "latency": {
                    "min": min(latencies),
                    "max": max(latencies),
                    "mean": statistics.mean(latencies),
                    "median": statistics.median(latencies),
                    "p50": statistics.quantiles(latencies, n=100)[49] if len(latencies) >= 100 else statistics.median(latencies),
                    "p95": statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 100 else max(latencies),
                    "p99": statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
                    "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0
                },
                "errors": dict(self.metrics["errors"])
            }
        else:
            metrics_summary = {
                "error": "No se completaron peticiones exitosamente"
            }
        
        # Guardar en JSON
        metrics_file = self.log_file.with_suffix('.json')
        with open(metrics_file, 'w') as f:
            json.dump(metrics_summary, f, indent=2)
        
        print(f"\n📊 Métricas guardadas: {metrics_file}")
        
        return metrics_summary
    
    async def run(self):
        """Ejecuta la simulación"""
        print("\n" + "="*80)
        print("SIMULADOR DE TRÁFICO - SISTEMA DE RECOMENDACIÓN")
        print("="*80)
        print(f"\n⚙️  Configuración:")
        print(f"  Rate: {self.rate} req/s")
        print(f"  Duración: {self.duration}s ({self.duration/60:.1f} min)")
        print(f"  Total esperado: ~{int(self.rate * self.duration)} peticiones")
        print(f"  Endpoint: {Config.API_BASE_URL}")
        print("\n" + "="*80 + "\n")
        
        # Setup logging
        self.setup_logging()
        
        # Verificar que la API está disponible
        print("🔍 Verificando API...")
        health_response = await self.client.get("/recommendations/health")
        
        if not health_response["success"]:
            print(f"❌ ERROR: API no disponible")
            print(f"   Asegúrate de que el sistema esté corriendo: docker-compose up -d")
            return
        
        print(f"✅ API disponible (latency: {health_response['latency']*1000:.0f}ms)")
        print(f"   Versión del modelo: {health_response['data'].get('model_version', 'unknown')}")
        print("\n🚀 Iniciando simulación...\n")
        
        # Iniciar simulación
        self.metrics["start_time"] = datetime.now()
        
        tasks = []
        start_time = time.time()
        next_request_time = start_time
        
        while time.time() - start_time < self.duration:
            current_time = time.time()
            
            # Si es hora de la siguiente petición
            if current_time >= next_request_time:
                task = asyncio.create_task(self.make_request())
                tasks.append(task)
                next_request_time += self.interval
                
                # Imprimir progreso cada segundo
                if int(current_time - start_time) % 1 == 0:
                    self.print_progress(current_time - start_time)
            
            # Pequeña pausa para no saturar CPU
            await asyncio.sleep(0.001)
        
        # Esperar a que terminen todas las peticiones
        print("\n\n⏳ Esperando a que terminen las peticiones pendientes...")
        await asyncio.gather(*tasks)
        
        self.metrics["end_time"] = datetime.now()
        
        print("\n✅ Simulación completada\n")
        
        # Guardar y mostrar métricas
        metrics = self.save_metrics()
        self.print_summary(metrics)
    
    def print_summary(self, metrics: Dict):
        """Imprime resumen de métricas"""
        print("\n" + "="*80)
        print("RESUMEN DE MÉTRICAS")
        print("="*80 + "\n")
        
        if "error" in metrics:
            print(f"❌ {metrics['error']}")
            return
        
        print(f"📊 Peticiones:")
        print(f"  Total:     {metrics['requests']['total']:,}")
        print(f"  Exitosas:  {metrics['requests']['successful']:,} ({metrics['requests']['success_rate']:.1f}%)")
        print(f"  Fallidas:  {metrics['requests']['failed']:,}")
        print(f"  Rate real: {metrics['requests']['actual_rate']:.1f} req/s")
        
        print(f"\n⏱️  Latencia:")
        print(f"  Mínima:    {metrics['latency']['min']*1000:.0f} ms")
        print(f"  Media:     {metrics['latency']['mean']*1000:.0f} ms")
        print(f"  Mediana:   {metrics['latency']['median']*1000:.0f} ms")
        print(f"  P95:       {metrics['latency']['p95']*1000:.0f} ms")
        print(f"  P99:       {metrics['latency']['p99']*1000:.0f} ms")
        print(f"  Máxima:    {metrics['latency']['max']*1000:.0f} ms")
        print(f"  Desv. Est: {metrics['latency']['stdev']*1000:.0f} ms")
        
        if metrics['errors']:
            print(f"\n❌ Errores:")
            for error, count in metrics['errors'].items():
                print(f"  {error}: {count}")
        
        print("\n" + "="*80 + "\n")


# ==========================================
# Main
# ==========================================

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="Simulador de tráfico HTTP para sistema de recomendación"
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10,
        help="Peticiones por segundo (default: 10)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duración en segundos (default: 60)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="URL base de la API (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Actualizar configuración
    Config.API_BASE_URL = args.url
    
    # Crear y ejecutar simulador
    simulator = TrafficSimulator(rate=args.rate, duration=args.duration)
    
    try:
        asyncio.run(simulator.run())
    except KeyboardInterrupt:
        print("\n\n⚠️  Simulación interrumpida por el usuario")
        simulator.metrics["end_time"] = datetime.now()
        
        if simulator.metrics["total_requests"] > 0:
            print("\nGuardando métricas parciales...")
            metrics = simulator.save_metrics()
            simulator.print_summary(metrics)


if __name__ == "__main__":
    main()
