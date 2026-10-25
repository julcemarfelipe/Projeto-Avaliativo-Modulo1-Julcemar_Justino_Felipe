import sys
from pathlib import Path
import pandas as pd

from banco import conectar, executar, inserir_em_lote
from config import ARQUIVOS

NOME_BANCO = "viagens_transparencia"
PASTA_DADOS = Path("data")
LIMITE_LINHAS = 150


def testar_amostra_csv(conexao, tabela: str, caminho_csv: Path) -> bool:
    """Carrega uma amostra de 150 linhas na tabela Raw para teste rápido."""
    try:
        print(f"  → 🧹 Esvaziando tabela '{tabela}' (TRUNCATE)...")
        executar(conexao, f"TRUNCATE TABLE {tabela}", commit=True)

        print(f"  → 📖 Lendo primeiras {LIMITE_LINHAS} linhas de '{caminho_csv.name}'...")
        # nrows=LIMITE_LINHAS garante a leitura rápida apenas da amostra
        df_amostra = pd.read_csv(
            caminho_csv,
            sep=";",
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
            nrows=LIMITE_LINHAS,
        )

        # Trata valores vazios para NULL nativo no banco
        df_tratado = df_amostra.replace({"": None})

        # Insere a amostra usando a função utilitária do projeto
        if inserir_em_lote(conexao, tabela, df_tratado):
            print(f"  ✓ Amostra inserida com sucesso: {len(df_tratado)} linhas em '{tabela}'.\n")
            return True
        else:
            print(f"  ❌ Falha reportada por inserir_em_lote na tabela '{tabela}'.\n")
            return False

    except Exception as erro:
        print(f"  ❌ Erro durante o teste em '{caminho_csv.name}': {erro}\n")
        return False


def main():
    print("=" * 60)
    print(f"🧪 TESTE DE CARGA RÁPIDA: CAMADA RAW ({LIMITE_LINHAS} LINHAS)")
    print(f"🎯 Banco de Dados: {NOME_BANCO}")
    print("=" * 60 + "\n")

    if not PASTA_DADOS.exists():
        print(f"❌ Diretório não encontrado: {PASTA_DADOS}")
        sys.exit(1)

    conexao = conectar(NOME_BANCO)
    if conexao is None:
        print(f"❌ Falha de ligação ao banco '{NOME_BANCO}'.")
        sys.exit(1)

    print(f"🔌 Ligado ao banco '{NOME_BANCO}' com sucesso!\n")

    try:
        sucesso_total = True
        for csv_nome, tabela_nome in ARQUIVOS.items():
            csv_path = PASTA_DADOS / csv_nome
            print(f"📥 Testando '{csv_nome}' -> Tabela '{tabela_nome}'...")

            if not csv_path.exists():
                print(f"❌ Ficheiro não encontrado: {csv_path}")
                sucesso_total = False
                break

            if not testar_amostra_csv(conexao, tabela_nome, csv_path):
                sucesso_total = False
                break

        print("=" * 60)
        if sucesso_total:
            print(f"✅ Teste concluído! Todas as tabelas receberam {LIMITE_LINHAS} linhas.")
        else:
            print("❌ O teste apresentou falhas em uma ou mais tabelas.")
        print("=" * 60)

    finally:
        conexao.close()
        print("🔒 Conexão com o banco fechada.")


if __name__ == "__main__":
    main()