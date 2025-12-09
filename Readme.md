cd c:\Users\sergi\OneDrive\Documentos\GitHub\app_cli
pip install -r requirements.txt

# Listar Conectores activos
python main.py list-hosts

# Solicitar un DataSet
python main.py request 00-15-5d-7b-e4-b0 dataset_1kb.json

# Ver métricas
python main.py metrics