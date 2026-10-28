import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Dicionário com configurações do PostgreSQL
POSTGRES_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'port': os.environ.get('PG_PORT', '5432'),
    'user': os.environ.get('PG_USER', 'postgres'),
    'password': os.environ.get('PG_PASSWORD', '1234'),
    'dbname': os.environ.get('PG_DATABASE', 'viagens_transparencia'),
}

# Dicionário mapeando CSVs para tabelas
ARQUIVOS = {
     "raw_viagens": "2025_Viagem.csv",
    "raw_pagamentos": "2025_Pagamento.csv",
    "raw_passagens": "2025_Passagem.csv",
    "raw_trechos": "2025_Trecho.csv",
}
