cd c:\Users\sergi\OneDrive\Documentos\GitHub\app_cli
pip install -r requirements.txt

# Listar Conectores activos
python main.py list-hosts

# Solicitar un DataSet
python main.py request cc-28-aa-cd-5c-74 dataset_1kb.json

# Ver métricas
python main.py metrics

# Otros
python main.py status <request_id>

# Listar Conectores activos
python main.py list-hosts

# Mostrar el output

-o output50mb_B.json

# Patrón A: Buffering (respuesta síncrona)

python main.py request-sync cc-28-aa-cd-5c-74 dataset_100mb.csv

# Patrón B: Streaming (chunks en tiempo real)

python main.py request-stream cc-28-aa-cd-5c-74 dataset_100mb.csv

# Patrón C: Offloading (MinIO)

python main.py request-offload cc-28-aa-cd-5c-74 dataset_100mb.csv