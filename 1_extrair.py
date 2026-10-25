import sys
from pathlib import Path
import pandas as pd

from banco import conectar, executar, inserir_em_lote

# -------------------------------------------------------------
# Configurações do Projeto
# -------------------------------------------------------------
DB_NOME = "viagens_transparencia"
DATA_DIR = Path(__file__).resolve().parent / "data"

# Mapeamento: Arquivo CSV -> Tabela de destino na Raw
MAPEAMENTO_ARQUIVOS = {
    "2025_Viagem.csv": "raw_viagem",
    "2025_Pagamento.csv": "raw_pagamento",
    "2025_Passagem.csv": "raw_passagem",
    "2025_Trecho.csv": "raw_trecho",
}

CHUNK_SIZE = 50000


def verificar_arquivos_csv() -> bool:
    """Verifica se os 4 arquivos CSV estão disponíveis na pasta data/."""
    if not DATA_DIR.exists():
        print(f"❌ Diretório não encontrado: {DATA_DIR}")
        return False

    arquivos_faltantes = [
        csv_nome for csv_nome in MAPEAMENTO_ARQUIVOS.keys()
        if not (DATA_DIR / csv_nome).exists()
    ]

    if arquivos_faltantes:
        print("❌ Faltam arquivos na pasta 'data/':")
        for nome in arquivos_faltantes:
            print(f"   • {nome}")
        return False

    return True


def carregar_csv(conexao, tabela: str, caminho_csv: Path) -> bool:
    """
    Limpa a tabela raw via TRUNCATE e faz a carga em blocos (chunks).
    Preserva todos os campos como string (fiel ao CSV original).
    """
    try:
        # 1. Idempotência: Esvazia a tabela antes da nova carga
        print(f"  ↳ 🧹 Limpando tabela '{tabela}' (TRUNCATE)...")
        executar(conexao, f"TRUNCATE TABLE {tabela}", commit=True)

        # 2. Leitura e ingestão em chunks
        print(f"  ↳ 📖 Lendo '{caminho_csv.name}' em blocos de {CHUNK_SIZE:,} linhas...")
        total_linhas = 0

        chunks = pd.read_csv(
            caminho_csv,
            sep=";",
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
            chunksize=CHUNK_SIZE
        )

        for chunk in chunks:
            # Substitui strings vazias por None para inserir como NULL
            chunk_tratado = chunk.replace({"": None})
            
            sucesso = inserir_em_lote(conexao, tabela, chunk_tratado)
            if not sucesso:
                raise RuntimeError(f"Falha ao inserir lote na tabela {tabela}.")

            total_linhas += len(chunk_tratado)
            print(f"     ↳ {total_linhas:,} linhas inseridas...")

        print(f"  ✅ Concluído: {total_linhas:,} linhas carregadas em '{tabela}'.\n")
        return True

    except Exception as erro:
        print(f"  ❌ Erro ao processar '{caminho_csv.name}': {erro}\n")
        return False


def main():
    print("=" * 60)
    print("🚀 FASE 1: EXTRAÇÃO E CARGA NA CAMADA RAW")
    print(f"🎯 Banco de Dados: {DB_NOME}")
    print("=" * 60 + "\n")

    # 1. Validação de pré-requisitos dos dados
    if not verificar_arquivos_csv():
        print("\n❌ Execução interrompida. Certifique-se de descompactar os CSVs em 'data/'.")
        sys.exit(1)

    # 2. Conexão ao banco de dados
    conexao = conectar(DB_NOME)
    if conexao is None:
        print(f"❌ Não foi possível conectar ao banco '{DB_NOME}'. Verifique seu .env.")
        sys.exit(1)

    print("🔌 Conectado ao banco de dados com sucesso!\n")

    # 3. Carga iterativa para cada tabela Raw
    try:
        for csv_nome, tabela_nome in MAPEAMENTO_ARQUIVOS.items():
            csv_path = DATA_DIR / csv_nome
            print(f"📥 Processando '{csv_nome}' -> Tabela '{tabela_nome}':")

            if not carregar_csv(conexao, tabela_nome, csv_path):
                print(f"❌ Falha na carga da tabela '{tabela_nome}'.")
                sys.exit(1)

        print("=" * 60)
        print("✅ Fase 1 concluída com sucesso! Camada Raw populada.")
        print("=" * 60)

    finally:
        conexao.close()


if __name__ == "__main__":
    main()