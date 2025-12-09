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
    
    def request_dataset_sync(
        self,
        mac_address: str,
        dataset_name: str,
        timeout: int = 60
    ) -> DatasetResponse:
        """
        Patrón A: Solicita un DataSet y espera respuesta completa.
        
        Args:
            mac_address: MAC del Conector destino
            dataset_name: Nombre del archivo
            timeout: Tiempo máximo de espera
            
        Returns:
            DatasetResponse con datos completos y métricas
        """
        url = f"{self.base_url}/datasets/request-sync"
        
        # t0: Aplicación envía solicitud
        t0 = time.time_ns() / 1e9
        
        try:
            response = self.session.post(
                url,
                json={
                    "mac_address": mac_address,
                    "dataset_name": dataset_name
                },
                params={"timeout": timeout},
                timeout=timeout + 5  # Dar margen extra al HTTP timeout
            )
            
            # t4: Respuesta recibida
            t4 = time.time_ns() / 1e9
            
            if response.status_code != 200:
                return DatasetResponse(
                    request_id="",
                    status="error",
                    error_message=f"HTTP {response.status_code}: {response.text}",
                    t0_sent=t0,
                    t4_received=t4
                )
            
            data = response.json()
            
            return DatasetResponse(
                request_id=data.get("request_id", ""),
                status=data.get("status", "completed"),
                data=data.get("data"),
                data_size_bytes=data.get("data_size_bytes"),
                timestamps=data.get("timestamps"),
                t0_sent=t0,
                t4_received=t4
            )
            
        except requests.Timeout:
            return DatasetResponse(
                request_id="",
                status="timeout",
                error_message=f"Timeout después de {timeout} segundos",
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )
        except requests.RequestException as e:
            return DatasetResponse(
                request_id="",
                status="error",
                error_message=str(e),
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )
    
    def health_check(self) -> bool:
        """Verifica si el Enrutador está activo."""
        url = f"{self.base_url}/health"
        
        try:
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    # =========================================================================
    # Patrón B: Streaming
    # =========================================================================
    
    def request_dataset_stream(
        self,
        mac_address: str,
        dataset_name: str,
        output_file: str = None
    ) -> DatasetResponse:
        """
        Patrón B: Solicita un DataSet y lo consume como stream.
        
        Args:
            mac_address: MAC del Conector destino
            dataset_name: Nombre del archivo
            output_file: Archivo donde guardar los datos (opcional)
            
        Returns:
            DatasetResponse con métricas
        """
        # t0: Envío de solicitud
        t0 = time.time_ns() / 1e9
        
        # 1. Solicitar stream
        request_url = f"{self.base_url}/datasets/request-stream"
        try:
            response = self.session.post(
                request_url,
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
                    error_message=f"HTTP {response.status_code}",
                    t0_sent=t0,
                    t4_received=time.time_ns() / 1e9
                )
            
            data = response.json()
            request_id = data.get("request_id", "")
            stream_url = data.get("stream_url", "")
            
        except requests.RequestException as e:
            return DatasetResponse(
                request_id="",
                status="error",
                error_message=str(e),
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )
        
        # 2. Esperar un momento para que el Conector inicie el stream
        time.sleep(0.5)
        
        # 3. Consumir el stream
        consume_url = f"{self.base_url}{stream_url}"
        
        try:
            stream_response = self.session.get(
                consume_url,
                stream=True,
                timeout=120
            )
            
            if stream_response.status_code != 200:
                return DatasetResponse(
                    request_id=request_id,
                    status="error",
                    error_message=f"Stream HTTP {stream_response.status_code}",
                    t0_sent=t0,
                    t4_received=time.time_ns() / 1e9
                )
            
            # t_first_byte: Primer chunk recibido
            t_first_byte = None
            total_bytes = 0
            chunks_received = 0
            
            # Archivo de salida (opcional)
            output_handle = None
            if output_file:
                output_handle = open(output_file, 'wb')
            
            # Buffer para detectar marcador de finalización
            timestamps_from_stream = {}
            pending_buffer = b""  # Buffer para datos pendientes
            
            try:
                for chunk in stream_response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    
                    if t_first_byte is None:
                        t_first_byte = time.time_ns() / 1e9
                    
                    # Agregar al buffer pendiente
                    pending_buffer += chunk
                    
                    # Verificar si contiene el marcador de finalización
                    if b"---STREAM_COMPLETE---" in pending_buffer:
                        # Encontrar posición del marcador
                        marker_pos = pending_buffer.find(b"\n---STREAM_COMPLETE---")
                        if marker_pos == -1:
                            marker_pos = pending_buffer.find(b"---STREAM_COMPLETE---")
                        
                        # Extraer datos antes del marcador
                        if marker_pos > 0:
                            data_chunk = pending_buffer[:marker_pos]
                            total_bytes += len(data_chunk)
                            chunks_received += 1
                            if output_handle:
                                output_handle.write(data_chunk)
                        
                        # Parsear timestamps del JSON después del marcador
                        try:
                            import json
                            marker_str = b"---STREAM_COMPLETE---"
                            marker_end = pending_buffer.find(marker_str)
                            if marker_end != -1:
                                json_start = marker_end + len(marker_str)
                                remaining = pending_buffer[json_start:].lstrip(b"\n\r")
                                if remaining:
                                    json_data = remaining.decode('utf-8').strip()
                                    if json_data:
                                        completion_info = json.loads(json_data)
                                        timestamps_from_stream = {
                                            "t1_received": completion_info.get("t1_received"),
                                            "t2_received": completion_info.get("t2_received"),
                                            "t3_start_send": completion_info.get("t3_start_send")
                                        }
                        except (json.JSONDecodeError, Exception) as e:
                            import sys
                            print(f"[DEBUG] Error parsing stream completion: {e}", file=sys.stderr)
                            print(f"[DEBUG] Buffer content: {pending_buffer[-200:]}", file=sys.stderr)
                        break
                    else:
                        # No hay marcador, escribir buffer excepto los últimos bytes (pueden ser parte del marcador)
                        safe_len = len(pending_buffer) - 50  # Mantener últimos 50 bytes
                        if safe_len > 0:
                            data_to_write = pending_buffer[:safe_len]
                            total_bytes += len(data_to_write)
                            chunks_received += 1
                            if output_handle:
                                output_handle.write(data_to_write)
                            pending_buffer = pending_buffer[safe_len:]
                
            finally:
                if output_handle:
                    output_handle.close()
            
            # t4: Stream completo
            t4 = time.time_ns() / 1e9
            
            return DatasetResponse(
                request_id=request_id,
                status="completed",
                data_size_bytes=total_bytes,
                t0_sent=t0,
                t4_received=t4,
                timestamps=timestamps_from_stream if timestamps_from_stream else None
            )
            
        except requests.RequestException as e:
            return DatasetResponse(
                request_id=request_id,
                status="error",
                error_message=str(e),
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )
    
    # =========================================================================
    # Patrón C: Offloading
    # =========================================================================
    
    def request_dataset_offload(
        self,
        mac_address: str,
        dataset_name: str,
        output_file: str = None,
        timeout: int = 60
    ) -> DatasetResponse:
        """
        Patrón C: Solicita un DataSet con offloading a MinIO.
        
        1. Solicita el dataset al Enrutador
        2. Hace polling hasta obtener la download_url
        3. Descarga directamente desde MinIO
        
        Args:
            mac_address: MAC del Conector destino
            dataset_name: Nombre del archivo
            output_file: Archivo donde guardar (opcional)
            timeout: Timeout total en segundos
            
        Returns:
            DatasetResponse con métricas
        """
        t0 = time.time_ns() / 1e9
        
        # 1. Solicitar offload
        request_url = f"{self.base_url}/datasets/request-offload"
        try:
            response = self.session.post(
                request_url,
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
                    error_message=f"HTTP {response.status_code}",
                    t0_sent=t0,
                    t4_received=time.time_ns() / 1e9
                )
            
            data = response.json()
            request_id = data.get("request_id", "")
            
        except requests.RequestException as e:
            return DatasetResponse(
                request_id="",
                status="error",
                error_message=str(e),
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )
        
        # 2. Polling hasta obtener download_url
        poll_url = f"{self.base_url}/datasets/{request_id}/status"
        download_url = None
        data_size = 0
        timestamps_from_status = {}
        
        for _ in range(int(timeout / self.poll_interval)):
            try:
                status_response = self.session.get(poll_url, timeout=self.timeout)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("status") == "completed":
                        download_url = status_data.get("download_url")
                        data_size = status_data.get("data_size_bytes", 0)
                        # Extraer timestamps del status
                        timestamps_from_status = status_data.get("timestamps") or {}
                        break
                    elif status_data.get("status") == "error":
                        return DatasetResponse(
                            request_id=request_id,
                            status="error",
                            error_message=status_data.get("error_message"),
                            t0_sent=t0,
                            t4_received=time.time_ns() / 1e9
                        )
            except requests.RequestException:
                pass
            time.sleep(self.poll_interval)
        
        if not download_url:
            return DatasetResponse(
                request_id=request_id,
                status="timeout",
                error_message="Timeout waiting for download_url",
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )
        
        # 3. Descargar desde MinIO
        try:
            download_response = self.session.get(download_url, stream=True, timeout=120)
            
            if download_response.status_code != 200:
                return DatasetResponse(
                    request_id=request_id,
                    status="error",
                    error_message=f"Download HTTP {download_response.status_code}",
                    t0_sent=t0,
                    t4_received=time.time_ns() / 1e9
                )
            
            total_bytes = 0
            if output_file:
                with open(output_file, 'wb') as f:
                    for chunk in download_response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            total_bytes += len(chunk)
            else:
                for chunk in download_response.iter_content(chunk_size=65536):
                    if chunk:
                        total_bytes += len(chunk)
            
            t4 = time.time_ns() / 1e9
            
            return DatasetResponse(
                request_id=request_id,
                status="completed",
                data_size_bytes=total_bytes or data_size,
                t0_sent=t0,
                t4_received=t4,
                timestamps=timestamps_from_status if timestamps_from_status else None
            )
            
        except requests.RequestException as e:
            return DatasetResponse(
                request_id=request_id,
                status="error",
                error_message=str(e),
                t0_sent=t0,
                t4_received=time.time_ns() / 1e9
            )

