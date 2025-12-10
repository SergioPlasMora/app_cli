# Flujo de Comunicación del Sistema

## Arquitectura General

Este sistema permite transferir datos desde **Nodos on-premise** (Conector) hacia una **Aplicación en la nube** (App CLI) a través de un **Enrutador** central, sin exponer puertos en las máquinas cliente.

---

## Resumen Visual

```
     App CLI                    Enrutador                    Conector
        │                           │                            │
        │                           │◄───── Conexión SSE/WS ─────│ (1)
        │                           │       (persistente)        │
        │                           │                            │
        │── POST request-sync ─────►│                            │ (2)
        │   (espera respuesta)      │                            │
        │                           │                            │
        │                           │──── Comando SSE/WS ───────►│ (3)
        │                           │                            │
        │                           │◄─── POST /datasets/result ─│ (4)
        │                           │     (datos)                │
        │                           │                            │
        │◄──── Respuesta JSON ──────│                            │ (5)
        │                           │                            │
```

---

## Flujo General (Aplica a todos los patrones)

┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 1: Conector se conecta al Enrutador (conexión persistente)            │
└─────────────────────────────────────────────────────────────────────────────┘

    Conector ─────────SSE/WebSocket─────────► Enrutador
              "Estoy listo para recibir comandos"
              (Conexión abierta esperando)


┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 2: App CLI solicita datos al Enrutador                                │
└─────────────────────────────────────────────────────────────────────────────┘

    App CLI ──────POST /datasets/request-sync──────► Enrutador
              {mac: "cc-28-aa...", dataset: "100mb.csv"}
              
    El Enrutador ESPERA (no responde aún)


┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 3: Enrutador envía comando al Conector por SSE/WebSocket              │
└─────────────────────────────────────────────────────────────────────────────┘

    Enrutador ────────SSE/WebSocket────────► Conector
               {command: "get_dataset", dataset_name: "100mb.csv"}


┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 4: Conector lee el archivo y lo envía al Enrutador                    │
└─────────────────────────────────────────────────────────────────────────────┘

    Conector ───────POST /datasets/result───────► Enrutador
              {data: "...100MB de datos...", request_id: "..."}


┌─────────────────────────────────────────────────────────────────────────────┐
│ PASO 5: Enrutador responde al App CLI (que estaba esperando)               │
└─────────────────────────────────────────────────────────────────────────────┘

    Enrutador ──────────Respuesta JSON──────────► App CLI
               {status: "success", data: "...100MB..."}

---

# Patrones de Transferencia de Datos

## Patrón A: Buffering (Síncrono)

**Concepto:** El Enrutador espera a recibir TODO el dataset antes de responder al App CLI.

**Comando:** `python main.py request-sync <mac> <dataset>`

```
     App CLI                    Enrutador                    Conector
        │                           │                            │
        │── POST request-sync ─────►│                            │
        │   (esperando...)          │                            │
        │                           │──── get_dataset ──────────►│
        │                           │                            │
        │                           │                            │ Lee archivo
        │                           │                            │ completo
        │                           │                            │
        │                           │◄─── POST /datasets/result ─│
        │                           │     {data: "TODO el        │
        │                           │      archivo completo"}    │
        │                           │                            │
        │◄──── JSON completo ───────│                            │
        │                           │                            │
```

**Características:**
- ✅ Simple de implementar
- ✅ Respuesta única y completa
- ❌ Alto uso de RAM en Enrutador (almacena todo)
- ❌ El cliente espera hasta que todo esté listo

---

## Patrón B: Streaming (Chunks)

**Concepto:** Los datos fluyen chunk por chunk a través del Enrutador.

**Comando:** `python main.py request-stream <mac> <dataset>`

```
     App CLI                    Enrutador                    Conector
        │                           │                            │
        │── POST request-stream ───►│                            │
        │   (streaming response)    │                            │
        │                           │── get_dataset_stream ─────►│
        │                           │                            │
        │                           │                            │ Lee archivo
        │                           │◄── POST stream/init ───────│ en chunks
        │◄──── chunk 1 ─────────────│◄── POST stream/chunk ──────│
        │◄──── chunk 2 ─────────────│◄── POST stream/chunk ──────│
        │◄──── chunk 3 ─────────────│◄── POST stream/chunk ──────│
        │◄──── ...      ────────────│◄── ...                     │
        │◄──── chunk N ─────────────│◄── POST stream/complete ───│
        │                           │                            │
```

**Características:**
- ✅ Bajo uso de RAM (no almacena todo)
- ✅ El cliente recibe datos inmediatamente (bajo TTFB)
- ❌ Más complejo de implementar
- ❌ Manejo de errores más difícil

---

## Patrón C: Offloading (MinIO)

**Concepto:** El Conector sube a MinIO, la Aplicación descarga directamente.

**Comando:** `python main.py request-offload <mac> <dataset>`

```
     App CLI                    Enrutador                    Conector
        │                           │                            │
        │── POST request-offload ──►│                            │
        │   (esperando URL...)      │                            │
        │                           │── get_dataset_offload ────►│
        │                           │                            │
        │                           │                            │ Lee archivo
        │                           │                            │     │
        │                           │                            │     ▼
        │                           │                         ┌──────────┐
        │                           │                         │  MinIO   │
        │                           │                         │ (Storage)│
        │                           │                         └────┬─────┘
        │                           │                              │
        │                           │◄── POST /datasets/result ────│
        │                           │    {download_url: "http://   │
        │                           │     minio:9000/..."}         │
        │                           │                              │
        │◄──── {download_url} ──────│                              │
        │                           │                              │
        │──────────── Descarga directa de MinIO ──────────────────►│
        │                                                          │
```

**Características:**
- ✅ Mínimo uso de RAM en Enrutador (solo pasa URL)
- ✅ Ideal para archivos muy grandes (100MB+)
- ✅ App CLI descarga directamente del storage
- ❌ Requiere infraestructura adicional (MinIO)
- ❌ Latencia adicional del upload

---

## Tabla Comparativa

| Aspecto | Patrón A | Patrón B | Patrón C |
|---------|----------|----------|----------|
| **Nombre** | Buffering | Streaming | Offloading |
| **RAM Enrutador** | Alta | Baja | Mínima |
| **Complejidad** | Simple | Media | Media |
| **TTFB** | Alto | Bajo | Medio |
| **Ideal para** | Archivos pequeños | Archivos medianos | Archivos grandes |
| **Dependencias** | Ninguna | Ninguna | MinIO |

---

## Puntos Clave

| Conexión | Tipo | Dirección | Qué transmite |
|----------|------|-----------|---------------|
| Conector → Enrutador | SSE/WebSocket | Persistente | Comandos (pequeños) |
| Conector → Enrutador | HTTP POST | Por solicitud | Datos (grandes) |
| App CLI → Enrutador | HTTP POST | Por solicitud | Solicitudes y respuestas |
| App CLI → MinIO | HTTP GET | Solo Patrón C | Descarga directa |