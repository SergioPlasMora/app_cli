"""
Recolector y calculador de métricas de rendimiento.
"""
import csv
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class MetricEntry:
    """Entrada de métricas para una solicitud."""
    request_id: str
    dataset_name: str
    mac_address: str
    timestamp: str
    
    # Tiempos
    t0_sent: float
    t1_received: Optional[float] = None
    t2_received: Optional[float] = None
    t3_start_send: Optional[float] = None
    t4_received: float = 0
    
    # Resultado
    status: str = "pending"
    data_size_bytes: int = 0
    
    # Métricas calculadas
    ttfb_seconds: float = 0
    throughput_bytes_per_sec: float = 0
    enrutador_latency: float = 0
    conector_latency: float = 0
    
    def calculate_metrics(self):
        """Calcula las métricas basadas en timestamps."""
        if self.t4_received and self.t0_sent:
            self.ttfb_seconds = self.t4_received - self.t0_sent
            
            if self.data_size_bytes and self.ttfb_seconds > 0:
                self.throughput_bytes_per_sec = self.data_size_bytes / self.ttfb_seconds
        
        if self.t2_received and self.t1_received:
            self.enrutador_latency = self.t2_received - self.t1_received
        
        if self.t3_start_send and self.t2_received:
            self.conector_latency = self.t3_start_send - self.t2_received


class MetricsCollector:
    """Recolector de métricas de rendimiento."""
    
    def __init__(self, output_file: str = "metrics.csv"):
        self.output_file = output_file
        self.entries: List[MetricEntry] = []
    
    def add_entry(
        self,
        request_id: str,
        dataset_name: str,
        mac_address: str,
        t0_sent: float,
        t4_received: float,
        status: str,
        data_size_bytes: int = 0,
        timestamps: dict = None
    ) -> MetricEntry:
        """Agrega una entrada de métricas."""
        entry = MetricEntry(
            request_id=request_id,
            dataset_name=dataset_name,
            mac_address=mac_address,
            timestamp=datetime.now().isoformat(),
            t0_sent=t0_sent,
            t4_received=t4_received,
            status=status,
            data_size_bytes=data_size_bytes
        )
        
        if timestamps:
            entry.t1_received = timestamps.get("t1_received")
            entry.t2_received = timestamps.get("t2_received")
            entry.t3_start_send = timestamps.get("t3_start_send")
        
        entry.calculate_metrics()
        self.entries.append(entry)
        
        return entry
    
    def save_to_csv(self):
        """Guarda las métricas a CSV."""
        if not self.entries:
            return
        
        file_exists = os.path.exists(self.output_file)
        
        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                writer.writerow([
                    "timestamp", "request_id", "dataset_name", "mac_address",
                    "status", "data_size_bytes", "ttfb_seconds",
                    "throughput_bytes_per_sec", "t0", "t1", "t2", "t3", "t4"
                ])
            
            for entry in self.entries:
                writer.writerow([
                    entry.timestamp, entry.request_id, entry.dataset_name,
                    entry.mac_address, entry.status, entry.data_size_bytes,
                    f"{entry.ttfb_seconds:.6f}",
                    f"{entry.throughput_bytes_per_sec:.2f}",
                    entry.t0_sent, entry.t1_received, entry.t2_received,
                    entry.t3_start_send, entry.t4_received
                ])
    
    def get_summary(self) -> dict:
        """Obtiene resumen de métricas."""
        if not self.entries:
            return {"count": 0}
        
        successful = [e for e in self.entries if e.status == "completed"]
        
        if not successful:
            return {
                "count": len(self.entries),
                "successful": 0,
                "failed": len(self.entries)
            }
        
        ttfbs = [e.ttfb_seconds for e in successful]
        throughputs = [e.throughput_bytes_per_sec for e in successful if e.throughput_bytes_per_sec > 0]
        
        return {
            "count": len(self.entries),
            "successful": len(successful),
            "failed": len(self.entries) - len(successful),
            "avg_ttfb_seconds": sum(ttfbs) / len(ttfbs),
            "min_ttfb_seconds": min(ttfbs),
            "max_ttfb_seconds": max(ttfbs),
            "avg_throughput_bytes_per_sec": sum(throughputs) / len(throughputs) if throughputs else 0
        }
    
    def clear(self):
        """Limpia las entradas."""
        self.entries = []
