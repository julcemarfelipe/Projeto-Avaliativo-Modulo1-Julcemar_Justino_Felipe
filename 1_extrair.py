import pandas as pd
from pathlib import Path

from banco import conectar, executar, inserir_em_lote
from config import ARQUIVOS


def validar_csvs():
    """
    Verifica se todos os arquivos CSV necessários existem na pasta data/.
    """

    arquivos_faltando = []

    for csv_name in ARQUIVOS.keys():
        csv_path = Path("data") / csv_name

        if not csv_path.exists():
            arquivos_faltando.append(str(csv_path))

    if arquivos_faltando:
        print("❌ Os seguintes arquivos não foram encontrados:")

        for arquivo in arquivos_faltando:
            print(f"   - {arquivo}")

        print("\nExtraia os CSVs para a pasta 'data/' antes de executar a carga.")
        return False

    return True


def carregar_csv(tabela, arquivo_csv):
    """
    Lê um CSV e insere em uma tabela raw.

    Args:
        tabela: Nome da tabela no banco.
        arquivo_csv: Caminho do arquivo CSV.
    """

    conexao = conectar("viagens_transparencia")

    if conexao is None:
        print("❌ Não foi possível conectar ao banco")
        return False

    try:
        # Passo 1: Limpar a tabela
        print(f"  → Limpando tabela {tabela}...")
        executar(conexao, f"TRUNCATE TABLE {tabela}", commit=True)

        # Passo 2: Ler CSV em lotes
        print(f"  → Lendo {arquivo_csv}...")
        chunk_size = 50000

        total_linhas = 0

        for chunk in pd.read_csv(
            arquivo_csv,
            sep=";",
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
            chunksize=chunk_size
        ):
            # Passo 3: Inserir lote
            if inserir_em_lote(conexao, tabela, chunk):
                total_linhas += len(chunk)
                print(f"    → {total_linhas:,} linhas inseridas...")

        print(f"✓ Tabela {tabela}: {total_linhas:,} linhas carregadas\n")
        return True

    except Exception as e:
        print(f"❌ Erro ao carregar {arquivo_csv}: {e}")
        return False

    finally:
        conexao.close()


# ===== INÍCIO DO SCRIPT =====

print("=" * 60)
print("FASE 1: EXTRAIR DADOS PARA RAW")
print("=" * 60)
print()

# Verificar se todos os CSVs necessários existem
if not validar_csvs():
    print("❌ Fase 1 falhou!")
    exit(1)

# Carregar cada arquivo CSV
for csv_name, table_name in ARQUIVOS.items():

    csv_path = Path("data") / csv_name

    print(f"Carregando {csv_name}...")

    if not carregar_csv(table_name, csv_path):
        print(f"❌ Falha ao carregar {csv_name}")
        exit(1)

print("=" * 60)
print("✅ Fase 1 concluída com sucesso!")
print("=" * 60)