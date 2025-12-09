#!/usr/bin/env python3
"""
Aplicación CLI para solicitar DataSets del Enrutador.
Simula el comportamiento de una SPA o App Móvil.
"""
import argparse
import sys
import os
import yaml
from pathlib import Path

from api_client import APIClient, DatasetResponse
from metrics import MetricsCollector
from logger import setup_logger

# Rich para output bonito (si está disponible)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def load_config() -> dict:
    """Carga configuración desde config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    return {}


def create_client(config: dict) -> APIClient:
    """Crea el cliente API con la configuración."""
    enrutador = config.get("enrutador", {})
    polling = config.get("polling", {})
    
    return APIClient(
        base_url=enrutador.get("base_url", "http://localhost:8000"),
        timeout=enrutador.get("timeout", 30),
        poll_interval_ms=polling.get("interval_ms", 500),
        max_poll_attempts=polling.get("max_attempts", 60)
    )


def print_result(response: DatasetResponse, dataset_name: str):
    """Imprime el resultado de forma formateada."""
    if RICH_AVAILABLE:
        console = Console()
        
        if response.status == "completed":
            table = Table(title="✅ DataSet Request Complete", show_header=False)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Request ID", response.request_id)
            table.add_row("Dataset", dataset_name)
            table.add_row("Status", response.status)
            
            if response.data_size_bytes:
                table.add_row("Size", f"{response.data_size_bytes:,} bytes")
            
            # Métricas
            ttfb = response.t4_received - response.t0_sent
            table.add_row("TTFB", f"{ttfb:.3f}s")
            
            if response.data_size_bytes and ttfb > 0:
                throughput = response.data_size_bytes / ttfb
                table.add_row("Throughput", f"{throughput:,.0f} bytes/s")
            
            console.print(table)
        else:
            console.print(Panel(
                f"[red]Error: {response.error_message or response.status}[/red]",
                title="❌ Request Failed"
            ))
    else:
        # Fallback sin Rich
        print("\n" + "=" * 50)
        if response.status == "completed":
            print("✅ DataSet Request Complete")
            print(f"   Request ID: {response.request_id}")
            print(f"   Dataset:    {dataset_name}")
            print(f"   Size:       {response.data_size_bytes:,} bytes")
            ttfb = response.t4_received - response.t0_sent
            print(f"   TTFB:       {ttfb:.3f}s")
        else:
            print(f"❌ Error: {response.error_message or response.status}")
        print("=" * 50 + "\n")


def cmd_request(args, client: APIClient, metrics: MetricsCollector, logger):
    """Comando: request <mac> <dataset>."""
    logger.info(f"Solicitando DataSet: {args.dataset} de {args.mac}")
    
    response = client.request_dataset(
        mac_address=args.mac,
        dataset_name=args.dataset,
        wait_for_result=True
    )
    
    # Registrar métricas
    entry = metrics.add_entry(
        request_id=response.request_id,
        dataset_name=args.dataset,
        mac_address=args.mac,
        t0_sent=response.t0_sent,
        t4_received=response.t4_received,
        status=response.status,
        data_size_bytes=response.data_size_bytes or 0,
        timestamps=response.timestamps
    )
    
    # Guardar métricas
    metrics.save_to_csv()
    
    # Mostrar resultado
    print_result(response, args.dataset)
    
    # Log de métricas
    logger.info(f"TTFB: {entry.ttfb_seconds:.3f}s, Throughput: {entry.throughput_bytes_per_sec:.0f} bytes/s")


def cmd_status(args, client: APIClient, logger):
    """Comando: status <request_id>."""
    logger.info(f"Consultando estado de: {args.request_id}")
    
    result = client.get_status(args.request_id)
    
    if RICH_AVAILABLE:
        console = Console()
        import json
        console.print_json(json.dumps(result, indent=2))
    else:
        import json
        print(json.dumps(result, indent=2))


def cmd_list_hosts(args, client: APIClient, logger):
    """Comando: list-hosts."""
    logger.info("Listando Conectores activos...")
    
    result = client.list_active_hosts()
    
    if RICH_AVAILABLE:
        console = Console()
        
        if result.get("count", 0) == 0:
            console.print("[yellow]No hay Conectores activos[/yellow]")
            return
        
        table = Table(title=f"Conectores Activos ({result['count']})")
        table.add_column("MAC Address", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Connected At")
        table.add_column("Last Ping")
        
        for c in result.get("connectors", []):
            table.add_row(
                c.get("mac_address", ""),
                c.get("status", ""),
                c.get("connected_at", "")[:19] if c.get("connected_at") else "",
                c.get("last_ping", "")[:19] if c.get("last_ping") else ""
            )
        
        console.print(table)
    else:
        print(f"\nConectores Activos: {result.get('count', 0)}")
        for c in result.get("connectors", []):
            print(f"  - {c.get('mac_address')}: {c.get('status')}")


def cmd_metrics(args, metrics: MetricsCollector, logger):
    """Comando: metrics."""
    summary = metrics.get_summary()
    
    if RICH_AVAILABLE:
        console = Console()
        
        table = Table(title="📊 Métricas de Rendimiento")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        table.add_row("Total Requests", str(summary.get("count", 0)))
        table.add_row("Successful", str(summary.get("successful", 0)))
        table.add_row("Failed", str(summary.get("failed", 0)))
        
        if summary.get("avg_ttfb_seconds"):
            table.add_row("Avg TTFB", f"{summary['avg_ttfb_seconds']:.3f}s")
            table.add_row("Min TTFB", f"{summary['min_ttfb_seconds']:.3f}s")
            table.add_row("Max TTFB", f"{summary['max_ttfb_seconds']:.3f}s")
        
        if summary.get("avg_throughput_bytes_per_sec"):
            table.add_row("Avg Throughput", f"{summary['avg_throughput_bytes_per_sec']:,.0f} bytes/s")
        
        console.print(table)
    else:
        print("\n=== Métricas ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")


def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(
        description="Aplicación CLI para solicitar DataSets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py request 00-15-5d-7b-e4-b0 dataset_1kb.json
  python main.py status 16b95b80-6dec-4d5b-91ad-459486bd56c8
  python main.py list-hosts
  python main.py metrics
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Comando: request
    p_request = subparsers.add_parser("request", help="Solicita un DataSet")
    p_request.add_argument("mac", help="MAC address del Conector")
    p_request.add_argument("dataset", help="Nombre del DataSet")
    
    # Comando: status
    p_status = subparsers.add_parser("status", help="Consulta estado de solicitud")
    p_status.add_argument("request_id", help="ID de la solicitud")
    
    # Comando: list-hosts
    subparsers.add_parser("list-hosts", help="Lista Conectores activos")
    
    # Comando: metrics
    subparsers.add_parser("metrics", help="Muestra métricas")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Cargar configuración
    config = load_config()
    logging_config = config.get("logging", {})
    metrics_config = config.get("metrics", {})
    
    # Inicializar componentes
    logger = setup_logger(
        level=logging_config.get("level", "INFO"),
        format_type=logging_config.get("format", "text")
    )
    client = create_client(config)
    metrics = MetricsCollector(
        output_file=metrics_config.get("output_file", "metrics.csv")
    )
    
    # Verificar conexión al Enrutador
    if not client.health_check():
        logger.warning("⚠️  No se pudo conectar al Enrutador")
    
    # Ejecutar comando
    if args.command == "request":
        cmd_request(args, client, metrics, logger)
    elif args.command == "status":
        cmd_status(args, client, logger)
    elif args.command == "list-hosts":
        cmd_list_hosts(args, client, logger)
    elif args.command == "metrics":
        cmd_metrics(args, metrics, logger)


if __name__ == "__main__":
    main()
