#!/usr/bin/env python3
"""
Script de pruebas de carga para el Enrutador.
Simula múltiples usuarios concurrentes ejecutando requests de los 3 patrones.
"""
import argparse
import asyncio
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict
import statistics

# Importar del app_cli existente
sys.path.append(str(Path(__file__).parent.parent))

try:
    from api_client import APIClient, DatasetResponse
    from metrics import MetricsCollector
    from logger import setup_logger
except ImportError:
    print("Error: No se puede importar desde app_cli")
    print("Verifica que ../app_cli esté disponible")
    sys.exit(1)

# cc-28-aa-cd-5c-74
@dataclass
class LoadTestConfig:
    """Configuración de la prueba de carga."""
    enrutador_url: str = "http://localhost:8000"
    mac_address: str = "cc-28-aa-cd-5c-74"
    total_requests: int = 100  # Total de requests a ejecutar
    concurrency: int = 10      # Máximo de requests simultáneas
    pattern: str = "A"  # A, B, C, or "all"
    dataset_name: str = "dataset_1kb.json"
    timeout: int = 60
    ramp_up_seconds: int = 0  # Tiempo para escalonar usuarios


@dataclass
class LoadTestResult:
    """Resultado agregado de la prueba de carga."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_seconds: float = 0.0
    
    # Métricas de TTFB (Time To First Byte)
    ttfb_values: List[float] = field(default_factory=list)
    ttfb_min: float = 0.0
    ttfb_max: float = 0.0
    ttfb_avg: float = 0.0
    ttfb_p50: float = 0.0
    ttfb_p90: float = 0.0
    ttfb_p95: float = 0.0
    ttfb_p99: float = 0.0
    
    # Throughput
    throughput_values: List[float] = field(default_factory=list)
    throughput_avg: float = 0.0
    
    # Bytes transferidos
    total_bytes: int = 0
    
    # Requests por segundo
    requests_per_second: float = 0.0
    
    def calculate_statistics(self):
        """Calcula estadísticas agregadas."""
        if self.ttfb_values:
            self.ttfb_min = min(self.ttfb_values)
            self.ttfb_max = max(self.ttfb_values)
            self.ttfb_avg = statistics.mean(self.ttfb_values)
            self.ttfb_p50 = statistics.median(self.ttfb_values)
            
            sorted_ttfb = sorted(self.ttfb_values)
            self.ttfb_p90 = sorted_ttfb[int(len(sorted_ttfb) * 0.90)] if len(sorted_ttfb) > 0 else 0
            self.ttfb_p95 = sorted_ttfb[int(len(sorted_ttfb) * 0.95)] if len(sorted_ttfb) > 0 else 0
            self.ttfb_p99 = sorted_ttfb[int(len(sorted_ttfb) * 0.99)] if len(sorted_ttfb) > 0 else 0
        
        if self.throughput_values:
            self.throughput_avg = statistics.mean(self.throughput_values)
        
        if self.total_duration_seconds > 0:
            self.requests_per_second = self.total_requests / self.total_duration_seconds


def execute_request_pattern_a(client: APIClient, config: LoadTestConfig) -> DatasetResponse:
    """Ejecuta una request del Patrón A (Buffering)."""
    return client.request_dataset_sync(
        mac_address=config.mac_address,
        dataset_name=config.dataset_name,
        timeout=config.timeout
    )


def execute_request_pattern_b(client: APIClient, config: LoadTestConfig) -> DatasetResponse:
    """Ejecuta una request del Patrón B (Streaming)."""
    return client.request_dataset_stream(
        mac_address=config.mac_address,
        dataset_name=config.dataset_name
    )


def execute_request_pattern_c(client: APIClient, config: LoadTestConfig) -> DatasetResponse:
    """Ejecuta una request del Patrón C (Offloading)."""
    return client.request_dataset_offload(
        mac_address=config.mac_address,
        dataset_name=config.dataset_name,
        timeout=config.timeout
    )


def worker_thread(request_id: int, config: LoadTestConfig) -> DatasetResponse:
    """
    Thread worker que ejecuta UNA sola request.
    IGUAL QUE ARROW: Cada request es independiente para máxima concurrencia.
    
    Args:
        request_id: ID de la request
        config: Configuración de la prueba
    
    Returns:
        Respuesta de la request
    """
    # Crear nuevo cliente con conexión independiente para cada request
    client = APIClient(
        base_url=config.enrutador_url,
        timeout=config.timeout
    )
    
    try:
        if config.pattern == "A":
            response = execute_request_pattern_a(client, config)
        elif config.pattern == "B":
            response = execute_request_pattern_b(client, config)
        elif config.pattern == "C":
            response = execute_request_pattern_c(client, config)
        else:
            # Rotar entre patrones
            pattern_index = request_id % 3
            if pattern_index == 0:
                response = execute_request_pattern_a(client, config)
            elif pattern_index == 1:
                response = execute_request_pattern_b(client, config)
            else:
                response = execute_request_pattern_c(client, config)
        
        return response
        
    except Exception as e:
        print(f"[Request {request_id}] Error: {e}")
        return DatasetResponse(
            request_id="",
            status="error",
            error_message=str(e)
        )


def run_load_test(config: LoadTestConfig, logger) -> LoadTestResult:
    """
    Ejecuta la prueba de carga.
    IGUAL QUE ARROW: --requests N total, --concurrency M simultáneas.
    
    Args:
        config: Configuración de la prueba
        logger: Logger
    
    Returns:
        Resultado agregado
    """
    logger.info(f"🚀 Iniciando prueba de carga")
    logger.info(f"   Total requests: {config.total_requests}")
    logger.info(f"   Concurrencia:   {config.concurrency}")
    logger.info(f"   Patrón:         {config.pattern}")
    logger.info(f"   Dataset:        {config.dataset_name}")
    
    result = LoadTestResult()
    all_responses: List[DatasetResponse] = []
    
    # Timestamp de inicio
    start_time = time.perf_counter()
    
    # Ejecutar con ThreadPoolExecutor - IGUAL QUE ARROW
    with ThreadPoolExecutor(max_workers=config.concurrency) as executor:
        futures = []
        
        # CLAVE: Cada request individual es un task independiente
        for request_id in range(config.total_requests):
            future = executor.submit(worker_thread, request_id, config)
            futures.append(future)
        
        # Recolectar resultados conforme completan
        completed = 0
        for future in as_completed(futures):
            try:
                response = future.result()
                all_responses.append(response)
                completed += 1
                
                # Mostrar progreso cada 10%
                if completed % max(1, config.total_requests // 10) == 0:
                    logger.info(f"   Progreso: {completed}/{config.total_requests} requests completadas")
                
            except Exception as e:
                logger.error(f"   Error en worker: {e}")
    
    # Timestamp de fin
    end_time = time.perf_counter()
    result.total_duration_seconds = end_time - start_time
    
    # Procesar resultados
    result.total_requests = len(all_responses)
    
    for response in all_responses:
        if response.status == "completed":
            result.successful_requests += 1
            
            # TTFB
            if response.t0_sent and response.t4_received:
                ttfb = response.t4_received - response.t0_sent
                result.ttfb_values.append(ttfb)
            
            # Bytes
            if response.data_size_bytes:
                result.total_bytes += response.data_size_bytes
                
                # Throughput
                if response.t0_sent and response.t4_received:
                    duration = response.t4_received - response.t0_sent
                    if duration > 0:
                        throughput = response.data_size_bytes / duration
                        result.throughput_values.append(throughput)
        else:
            result.failed_requests += 1
    
    # Calcular estadísticas
    result.calculate_statistics()
    
    return result


def print_results(result: LoadTestResult, config: LoadTestConfig):
    """Imprime resultados de la prueba."""
    print("\n" + "=" * 80)
    print("📊 RESULTADOS DE LA PRUEBA DE CARGA")
    print("=" * 80)
    
    print(f"\n🔧 Configuración:")
    print(f"   Total requests: {config.total_requests}")
    print(f"   Concurrencia:   {config.concurrency}")
    print(f"   Patrón:         {config.pattern}")
    print(f"   Dataset:        {config.dataset_name}")
    
    print(f"\n📈 Resultados Generales:")
    print(f"   Total requests:        {result.total_requests}")
    print(f"   Exitosos:              {result.successful_requests} ({result.successful_requests/result.total_requests*100:.1f}%)")
    print(f"   Fallidos:              {result.failed_requests} ({result.failed_requests/result.total_requests*100:.1f}%)")
    print(f"   Duración total:        {result.total_duration_seconds:.2f}s")
    print(f"   Requests/segundo:      {result.requests_per_second:.2f}")
    
    if result.ttfb_values:
        print(f"\n⏱️  TTFB (Time To First Byte):")
        print(f"   Min:  {result.ttfb_min:.3f}s")
        print(f"   Max:  {result.ttfb_max:.3f}s")
        print(f"   Avg:  {result.ttfb_avg:.3f}s")
        print(f"   P50:  {result.ttfb_p50:.3f}s")
        print(f"   P90:  {result.ttfb_p90:.3f}s")
        print(f"   P95:  {result.ttfb_p95:.3f}s")
        print(f"   P99:  {result.ttfb_p99:.3f}s")
    
    if result.throughput_values:
        print(f"\n📦 Throughput:")
        print(f"   Avg:         {result.throughput_avg:,.0f} bytes/s")
        print(f"   Avg (MB/s):  {result.throughput_avg/1024/1024:.2f} MB/s")
    
    if result.total_bytes > 0:
        print(f"\n💾 Datos Transferidos:")
        print(f"   Total:  {result.total_bytes:,} bytes ({result.total_bytes/1024/1024:.2f} MB)")
    
    print("\n" + "=" * 80 + "\n")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Prueba de carga para el Enrutador",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # 1000 requests, 20 concurrentes (IGUAL QUE ARROW)
  python load_test.py --requests 1000 --concurrency 20 --pattern B --dataset dataset_1mb.csv
  
  # 500 requests, 50 concurrentes, todos los patrones
  python load_test.py --requests 500 --concurrency 50 --pattern all
  
  # 100 requests, 10 concurrentes, Patrón A
  python load_test.py --requests 100 --concurrency 10 --pattern A
        """
    )
    
    parser.add_argument("--url", default="http://localhost:8000", help="URL del Enrutador")
    parser.add_argument("--mac", default="cc-28-aa-cd-5c-74", help="MAC address del Conector")
    parser.add_argument("--requests", "-r", type=int, default=100, help="Total de requests a ejecutar")
    parser.add_argument("--concurrency", "-c", type=int, default=10, help="Requests simultáneas (paralelas)")
    parser.add_argument("--pattern", "-p", choices=["A", "B", "C", "all"], default="A", 
                        help="Patrón a probar (A=Buffering, B=Streaming, C=Offloading, all=mezclado)")
    parser.add_argument("--dataset", "-d", default="dataset_1kb.json", help="Nombre del dataset")
    parser.add_argument("--timeout", "-t", type=int, default=60, help="Timeout en segundos")
    
    args = parser.parse_args()
    
    # Configuración
    config = LoadTestConfig(
        enrutador_url=args.url,
        mac_address=args.mac,
        total_requests=args.requests,
        concurrency=args.concurrency,
        pattern=args.pattern,
        dataset_name=args.dataset,
        timeout=args.timeout
    )
    
    # Logger
    logger = setup_logger(level="INFO", format_type="text")
    
    # Verificar conexión al Enrutador
    client = APIClient(base_url=config.enrutador_url)
    if not client.health_check():
        logger.error("❌ No se puede conectar al Enrutador")
        logger.error(f"   URL: {config.enrutador_url}")
        sys.exit(1)
    
    logger.info(f"✅ Conectado al Enrutador: {config.enrutador_url}")
    
    # Ejecutar prueba
    try:
        result = run_load_test(config, logger)
        print_results(result, config)
        
        # Guardar resultados en CSV para análisis
        metrics_collector = MetricsCollector(output_file="load_test_results.csv")
        # Aquí podrías guardar los resultados agregados si lo necesitas
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Prueba interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
