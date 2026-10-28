import sys
from pathlib import Path
import pandas as pd
from banco import conectar, executar, inserir_em_lote

NOME_BANCO = "viagens_transparencia"
PASTA_DADOS = Path("data")
CHUNK_SIZE = 50000  # Processa de 50 mil em 50 mil linhas para otimizar memória

CONFIG_ARQUIVOS = {
     "2025_Viagem.csv": {
           "tabela": "raw_viagens",
           "colunas": {
               "Identificador do processo de viagem": "id_viagem",
               "Número da Proposta (PCDP)": "num_proposta",
               "Situação": "situacao",
               "Viagem Urgente": "viagem_urgente",
               "Justificativa Urgência Viagem": "justificativa_urgencia",
               "Código do órgão superior": "cod_orgao_superior",
               "Nome do órgão superior": "nome_orgao_superior",
               "Código órgão solicitante": "cod_orgao_solicitante",
               "Nome órgão solicitante": "nome_orgao_solicitante",
               "CPF viajante": "cpf_viajante",
               "Nome": "nome_viajante",
               "Cargo": "cargo",
               "Função": "funcao",
               "Descrição Função": "descricao_funcao",
               "Período - Data de início": "data_inicio",
               "Período - Data de fim": "data_fim",
               "Destinos": "destinos",
               "Motivo": "motivo",
               "Valor diárias": "valor_diarias",
               "Valor passagens": "valor_passagens",
               "Valor devolução": "valor_devolucao",
               "Valor outros gastos": "valor_outros_gastos",
           },
       },
       "2025_Pagamento.csv": {
           "tabela": "raw_pagamentos",
           "colunas": {
               "Identificador do processo de viagem": "id_viagem",
               "Número da Proposta (PCDP)": "num_proposta",
               "Código do órgão superior": "cod_orgao_superior",
               "Nome do órgão superior": "nome_orgao_superior",
               "Codigo do órgão pagador": "cod_orgao_pagador",
               "Nome do órgao pagador": "nome_orgao_pagador",
               "Código da unidade gestora pagadora": "cod_ug_pagadora",
               "Nome da unidade gestora pagadora": "nome_ug_pagadora",
               "Tipo de pagamento": "tipo_pagamento",
               "Valor": "valor",
           },
       },
       "2025_Passagem.csv": {
           "tabela": "raw_passagens",
           "colunas": {
               "Identificador do processo de viagem": "id_processo_viagem",
               "Número da Proposta (PCDP)": "num_proposta_pcdp",
               "Meio de transporte": "meio_transporte",
               "País - Origem ida": "pais_origem_ida",
               "UF - Origem ida": "uf_origem_ida",
               "Cidade - Origem ida": "cidade_origem_ida",
               "País - Destino ida": "pais_destino_ida",
               "UF - Destino ida": "uf_destino_ida",
               "Cidade - Destino ida": "cidade_destino_ida",
               "País - Origem volta": "pais_origem_volta",
               "UF - Origem volta": "uf_origem_volta",
               "Cidade - Origem volta": "cidade_origem_volta",
               "Pais - Destino volta": "pais_destino_volta",
               "UF - Destino volta": "uf_destino_volta",
               "Cidade - Destino volta": "cidade_destino_volta",
               "Valor da passagem": "valor_passagem",
               "Taxa de serviço": "taxa_servico",
               "Data da emissão/compra": "data_emissao_compra",
               "Hora da emissão/compra": "hora_emissao_compra",
           },
       },
       "2025_Trecho.csv": {
           "tabela": "raw_trechos",
           "colunas": {
               "Identificador do processo de viagem ": "id_processo_viagem",
               "Número da Proposta (PCDP)": "num_proposta_pcdp",
               "Sequência Trecho": "sequencia_trecho",
               "Origem - Data": "origem_data",
               "Origem - País": "origem_pais",
               "Origem - UF": "origem_uf",
               "Origem - Cidade": "origem_cidade",
               "Destino - Data": "destino_data",
               "Destino - País": "destino_pais",
               "Destino - UF": "destino_uf",
               "Destino - Cidade": "destino_cidade",
               "Meio de transporte": "meio_transporte",
               "Número Diárias": "numero_diarias",
               "Missao?": "missao",
           },
       },
   }

def carregar_dados_completos(conexao, arquivo_csv: str, cfg: dict) -> bool:
    caminho = PASTA_DADOS / arquivo_csv
    tabela = cfg["tabela"]
    mapa_colunas = cfg["colunas"]

    if not caminho.exists():
        print(f"❌ Arquivo não encontrado: {caminho}")
        return False

    try:
        # 1. Idempotência: limpa a tabela antes da nova carga
        print(f"  → 🧹 Esvaziando tabela '{tabela}' (TRUNCATE)...")
        executar(conexao, f"TRUNCATE TABLE {tabela}", commit=True)

        # 2. Leitura de todos os registros em blocos (chunks)
        print(f"  → 📖 Lendo '{arquivo_csv}' em blocos de {CHUNK_SIZE:,} linhas...")
        blocos = pd.read_csv(
            caminho,
            sep=";",
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
            chunksize=CHUNK_SIZE,
        )

        total_linhas = 0
        for chunk in blocos:
            # Filtra e renomeia apenas as colunas mapeadas que constam no arquivo
            colunas_disponiveis = {orig: dest for orig, dest in mapa_colunas.items() if orig in chunk.columns}
            chunk_filtrado = chunk[list(colunas_disponiveis.keys())].rename(columns=colunas_disponiveis)

            # Converte valores vazios para None para gravarem como NULL no banco
            chunk_tratado = chunk_filtrado.replace({"": None})

            # Inserção do bloco no banco
            if not inserir_em_lote(conexao, tabela, chunk_tratado):
                raise RuntimeError(f"Falha ao inserir lote na tabela '{tabela}'.")

            total_linhas += len(chunk_tratado)
            print(f"     ↳ {total_linhas:,} linhas inseridas...")

        print(f"  ✓ Tabela '{tabela}': carga concluída com {total_linhas:,} linhas.\n")
        return True

    except Exception as erro:
        print(f"  ❌ Erro ao carregar '{arquivo_csv}': {erro}\n")
        return False


def main():
    print("=" * 60)
    print("🚀 FASE 1: EXTRAÇÃO E CARGA TOTAL NA CAMADA RAW")
    print(f"🎯 Banco de Dados: {NOME_BANCO}")
    print("=" * 60 + "\n")

    if not PASTA_DADOS.exists():
        print(f"❌ Diretório não encontrado: {PASTA_DADOS}")
        sys.exit(1)

    conexao = conectar(NOME_BANCO)
    if conexao is None:
        print(f"❌ Falha de conexão ao banco '{NOME_BANCO}'.")
        sys.exit(1)

    print(f"🔌 Conectado ao banco '{NOME_BANCO}' com sucesso!\n")

    try:
        sucesso_total = True
        for arquivo_csv, cfg in CONFIG_ARQUIVOS.items():
            print(f"📥 Processando '{arquivo_csv}' -> Tabela '{cfg['tabela']}'...")
            if not carregar_dados_completos(conexao, arquivo_csv, cfg):
                sucesso_total = False
                break

        print("=" * 60)
        if sucesso_total:
            print("✅ Fase 1 concluída com sucesso! Toda a Camada Raw foi populada.")
        else:
            print("❌ A extração apresentou erros. Verifique os logs acima.")
        print("=" * 60)

    finally:
        conexao.close()
        print("🔒 Conexão com o banco fechada.")


if __name__ == "__main__":
    main()