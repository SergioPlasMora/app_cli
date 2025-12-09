cd c:\Users\sergi\OneDrive\Documentos\GitHub\app_cli
pip install -r requirements.txt

# Listar Conectores activos
python main.py list-hosts

# Solicitar un DataSet
python main.py request 00-15-5d-7b-e4-b0 dataset_1kb.json

# Ver métricas
python main.py metrics

# Otros
python main.py status <request_id>

# Listar Conectores activos
python main.py list-hosts

# Patrón A: Buffering (respuesta síncrona)

python main.py request-sync 00-15-5d-7b-e4-b0 dataset_100mb.csv
# Patrón B: Streaming (chunks en tiempo real)

python main.py request-stream 00-15-5d-7b-e4-b0 dataset_100mb.csv -o output.json

# Patrón C: Offloading (MinIO)
python main.py request-offload 00-15-5d-7b-e4-b0 dataset_100mb.csv -o output100mb_C.json

