cd c:\Users\sergi\OneDrive\Documentos\GitHub\app_cli
pip install -r requirements.txt

# Listar Conectores activos
python main.py list-hosts

# Solicitar un DataSet
python main.py request 10-51-07-96-d5-49 dataset_1kb.json

# Ver métricas
python main.py metrics

# Otros
python main.py status <request_id>

# Listar Conectores activos
python main.py list-hosts

# Mostrar el output

-o output50mb_B.json

# Patrón A: Buffering (respuesta síncrona)

python main.py request-sync 10-51-07-96-d5-49 dataset_50mb.csv

# Patrón B: Streaming (chunks en tiempo real)

python main.py request-stream 10-51-07-96-d5-49 dataset_50mb.csv

# Patrón C: Offloading (MinIO)

python main.py request-offload 10-51-07-96-d5-49 dataset_50mb.csv