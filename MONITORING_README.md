# Stack de Monitoreo - Luzzi Core IM Enrutador

Sistema completo de monitoreo con Prometheus, Grafana, Node Exporter y pruebas de carga basadas en tu `app_cli`.

## 🏗️ Componentes

| Componente | Puerto | Descripción |
|------------|--------|-------------|
| **Enrutador** | 8000 | API FastAPI con métricas instrumentadas |
| **Prometheus** | 9090 | Base de datos de series temporales |
| **Grafana** | 3000 | Dashboards y visualización (admin/admin123) |
| **Node Exporter** | 9100 | Métricas del sistema (CPU, memoria, disco) |
| **MinIO** | 9000/9001 | Storage para Patrón C |

## 🚀 Inicio Rápido

### 1. Levantar el stack completo

```bash
docker-compose up -d
```

### 2. Acceder a Grafana

```
URL: http://localhost:3000
User: admin
Pass: admin123
```

El dashboard "Luzzi Core IM Enrutador" se carga automáticamente.

### 3. Ver métricas en Prometheus

```
URL: http://localhost:9090
```

## 📊 Métricas Disponibles

### Métricas HTTP Generales
- `http_requests_total` - Total de requests por endpoint/método/status
- `http_request_duration_seconds` - Histograma de latencia

### Métricas por Patrón
- `pattern_requests_total{pattern="A|B|C"}` - Requests por patrón
- `pattern_duration_seconds{pattern="A|B|C"}` - Duración por patrón
- `pattern_bytes_transferred_total{pattern="A|B|C"}` - Bytes transferidos
- `pattern_errors_total{pattern="A|B|C"}` - Errores por patrón

### Métricas de Conexiones
- `active_sse_connections` - Conexiones SSE activas
- `active_websocket_connections` - Conexiones WebSocket activas
- `active_streams` - Streams activos (Patrón B)
- `stream_chunks_total` - Chunks enviados

### Métricas del Sistema (Node Exporter)
- CPU usage, memoria, disco I/O, red, etc.

## 🧪 Pruebas de Carga

**IMPORTANTE**: En lugar de Locust, usamos un script personalizado basado en tu `app_cli`.

### Script de Pruebas

Ubicación: `load_testing/load_test.py`

### Requisitos

El script importa de `app_cli`, así que necesitas tenerlo disponible:

```bash
# Desde luzzi-core-im-enrutador/
cd load_testing
python load_test.py --help
```

### Ejemplos de Uso

#### 100 usuarios concurrentes - Patrón A (Buffering)
```bash
python load_test.py --users 100 --pattern B --dataset dataset_1mb.csv
```

#### 1000 usuarios - Todos los patrones mezclados
```bash
```

#### 500 usuarios con ramp-up de 10 segundos
```bash
python load_test.py --users 500 --pattern B --ramp-up 10 --dataset dataset_30mb.csv
```

### Parámetros

| Parámetro | Descripción | Default |
|-----------|-------------|---------|
| `--url` | URL del Enrutador | http://localhost:8000 |
| `--mac` | MAC address del Conector | 00-15-5d-7b-e4-b0 |
| `--users`, `-u` | Usuarios concurrentes | 10 |
| `--requests`, `-r` | Requests por usuario | 1 |
| `--pattern`, `-p` | Patrón (A/B/C/all) | A |
| `--dataset`, `-d` | Nombre del dataset | dataset_1kb.json |
| `--timeout`, `-t` | Timeout en segundos | 60 |
| `--ramp-up` | Tiempo de escalado (segundos) | 0 |

### Métricas Recolectadas

El script muestra:
- Total requests (exitosos/fallidos)
- Requests por segundo
- TTFB (Min/Max/Avg/P50/P90/P95/P99)
- Throughput promedio
- Datos transferidos

## 📈 Dashboard de Grafana

El dashboard preconfigurado incluye:

### 📊 Sistema
- CPU Usage
- Memory Usage
- Disk I/O

### 🚀 Aplicación
- Requests por segundo
- Latencia (P50/P90/P99)
- Error Rate

### 🔄 Patrones de Transferencia
- Requests por patrón (A, B, C)
- Duración P95 por patrón
- Bytes transferidos por patrón

### 🔗 Conexiones
- Conexiones SSE activas
- Conexiones WebSocket activas
- Streams activos
- Chunks enviados/min

## 🔧 Configuración

### Prometheus

Archivo: `monitoring/prometheus.yml`

Scrape interval: 15s

Targets:
- `app:8000/metrics` - Enrutador
- `node-exporter:9100` - Sistema

### Grafana

Provisioning automático de:
- Datasource (Prometheus)
- Dashboard (Enrutador)

## 🛠️ Desarrollo

### Agregar nuevas métricas

1. Editar `utils/metrics.py`
2. Instrumentar el código relevante
3. Prometheus las detectará automáticamente
4. Agregarlas al dashboard de Grafana

### Reiniciar servicios

```bash
# Reiniciar todo
docker-compose restart

# Solo el enrutador
docker-compose restart app

# Recargar config de Prometheus (sin reiniciar)
curl -X POST http://localhost:9090/-/reload
```

## 📝 Notas

- **Retención de Prometheus**: 15 días (configurable en docker-compose.yml)
- **Ramp-up**: Escala gradualmente los usuarios para evitar picos
- **Thread Pool**: El script de load testing usa ThreadPoolExecutor para simular concurrencia real
