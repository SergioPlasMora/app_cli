"""
Cliente API para comunicación con el Enrutador.
"""
import time
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class DatasetResponse:
    """Respuesta de solicitud de DataSet."""
    request_id: str
    status: str
    data: Optional[str] = None
    data_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    timestamps: Optional[Dict[str, float]] = None
    
    # Métricas calculadas
    t0_sent: float = 0
    t4_received: float = 0


class APIClient:
    """Cliente para comunicación con el Enrutador."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: int = 30,
        poll_interval_ms: int = 500,
        max_poll_attempts: int = 60
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval_ms / 1000
        self.max_poll_attempts = max_poll_attempts
        self.session = requests.Session()
    
    def request_dataset(
        self,
        mac_address: str,
        dataset_name: str,
        wait_for_result: bool = True
    ) -> DatasetResponse:
        """
        Solicita un DataSet al Enrutador.
        
        Args:
            mac_address: MAC del Conector destino
            dataset_name: Nombre del archivo
            wait_for_result: Si True, hace polling hasta completar
            
        Returns:
            DatasetResponse con datos o estado
        """
        url = f"{self.base_url}/datasets/request"
        
        # t0: Aplicación envía solicitud
        t0 = time.time_ns() / 1e9
        
        try:
            response = self.session.post(
                url,
                json={
                    "mac_address": mac_address,
                    "dataset_name": dataset_name
                },
                timeout=self.timeout
            )
            
            if response.status_code not in (200, 202):
                return DatasetResponse(
                    request_id="",
                    status="error",
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    t0_sent=t0
                )
            
            data = response.json()
            request_id = data.get("request_id", "")
            
            if not wait_for_result:
                return DatasetResponse(
                    request_id=request_id,
                    status="pending",
                    t0_sent=t0
                )
            
            # Polling hasta obtener resultado
            return self._poll_for_result(request_id, t0)
            
        except requests.RequestException as e:
            return DatasetResponse(
                request_id="",
                status="error",
                error_message=str(e),
                t0_sent=t0
            )
    
    def _poll_for_result(self, request_id: str, t0: float) -> DatasetResponse:
        """Hace polling del estado hasta completar o timeout."""
        url = f"{self.base_url}/datasets/{request_id}/status"
        
        for attempt in range(self.max_poll_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code != 200:
                    time.sleep(self.poll_interval)
                    continue
                
                data = response.json()
                status = data.get("status", "pending")
                
                if status in ("completed", "error"):
                    # t4: Aplicación termina de recibir
                    t4 = time.time_ns() / 1e9
                    
                    return DatasetResponse(
                        request_id=request_id,
                        status=status,
                        data=data.get("data"),
                        data_size_bytes=data.get("data_size_bytes"),
                        error_message=data.get("error_message"),
                        timestamps=data.get("timestamps"),
                        t0_sent=t0,
                        t4_received=t4
                    )
                
                time.sleep(self.poll_interval)
                
            except requests.RequestException:
                time.sleep(self.poll_interval)
        
        # Timeout
        return DatasetResponse(
            request_id=request_id,
            status="timeout",
            error_message=f"Timeout after {self.max_poll_attempts} attempts",
            t0_sent=t0,
            t4_received=time.time_ns() / 1e9
        )
    
    def get_status(self, request_id: str) -> Dict[str, Any]:
        """Obtiene el estado de una solicitud."""
        url = f"{self.base_url}/datasets/{request_id}/status"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            return {"status": "error", "error": str(e)}
    
    def list_active_hosts(self) -> Dict[str, Any]:
        """Lista los Conectores activos."""
        url = f"{self.base_url}/hosts/active"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return {"count": 0, "connectors": [], "error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            return {"count": 0, "connectors": [], "error": str(e)}
    
    def health_check(self) -> bool:
        """Verifica si el Enrutador está activo."""
        url = f"{self.base_url}/health"
        
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
