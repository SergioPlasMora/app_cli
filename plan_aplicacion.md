# Plan de Implementación: Componente Aplicación (CLI)

**Proyecto:** SaaS de Analítica Descentralizada  
**Versión:** 1.0  
**Fecha:** 09 de Diciembre, 2025  
**Ubicación:** `c:\Users\sergi\OneDrive\Documentos\GitHub\app_cli\`

---

## 1. Objetivo

El componente **Aplicación** es un cliente CLI que simula el comportamiento de una SPA o App Móvil:

1. Solicitar DataSets al Enrutador
2. Esperar (polling) hasta que el Conector responda
3. Recibir los datos y medir métricas de rendimiento
4. Registrar timestamps t0 (envío) y t4 (recepción completa)

---

## 2. Estructura de Archivos

```
app_cli/
├── main.py              # Punto de entrada CLI
├── config.yaml          # Configuración
├── api_client.py        # Cliente HTTP para el Enrutador
├── metrics.py           # Recolector de métricas
├── logger.py            # Logging JSON
└── requirements.txt     # Dependencias
```

---

## 3. Comandos CLI

| Comando | Descripción |
|---------|-------------|
| `request <mac> <dataset>` | Solicita DataSet y espera respuesta |
| `status <request_id>` | Consulta estado de solicitud |
| `list-hosts` | Lista Conectores activos |
| `metrics` | Muestra métricas recolectadas |

---

## 4. Métricas

| Métrica | Fórmula | Descripción |
|---------|---------|-------------|
| **TTFB** | t4 - t0 | Tiempo total |
| **Throughput** | size / (t4 - t0) | Bytes/segundo |
