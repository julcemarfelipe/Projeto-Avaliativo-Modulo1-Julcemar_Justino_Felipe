import sys
from pathlib import Path
import pandas as pd
from banco import conectar, executar, inserir_em_lote

NOME_BANCO = "viagens_transparencia"
PASTA_DADOS = Path("data")
LIMITE_LINHAS = 150

# Mapeamento com a seleção e renomeação exata das colunas do 0_criar_banco.sql
CONFIG_AMOSTRAS = {
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
            "Codigo do orgao pagador": "cod_orgao_pagador",
            "Nome do orgao pagador": "nome_orgao_pagador",
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
            "País - Destino volta": "pais_destino_volta",
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
            "Identificador do processo de viagem": "id_processo_viagem",
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
            "Número de diárias": "numero_diarias",
            "Missão?": "missao",
        },
    },
}

def testar_amostra(conexao, arquivo_csv: str, cfg: dict) -> bool:
    caminho = PASTA_DADOS / arquivo_csv
    tabela = cfg["tabela"]
    mapa_colunas = cfg["colunas"]

    if not caminho.exists():
        print(f"❌ Ficheiro não encontrado: {caminho}")
        return False

    try:
        # 1. Limpeza da tabela (Idempotência)
        print(f"  → 🧹 Esvaziando tabela '{tabela}' (TRUNCATE)...")
        executar(conexao, f"TRUNCATE TABLE {tabela}", commit=True)

        # 2. Leitura da amostra de 150 linhas
        print(f"  → 📖 Lendo {LIMITE_LINHAS} linhas de '{arquivo_csv}'...")
        df_bruto = pd.read_csv(
            caminho,
            sep=";",
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
            nrows=LIMITE_LINHAS,
        )

        # 3. Filtrar apenas colunas existentes no CSV e renomear para casar com o SQL
        colunas_disponiveis = {orig: dest for orig, dest in mapa_colunas.items() if orig in df_bruto.columns}
        df_tratado = df_bruto[list(colunas_disponiveis.keys())].rename(columns=colunas_disponiveis)

        # Garante substituição de strings vazias por None (NULL no banco)
        df_tratado = df_tratado.replace({"": None})

        # 4. Inserção usando o método padrão do projeto
        if inserir_em_lote(conexao, tabela, df_tratado):
            print(f"  ✓ Amostra inserida com sucesso: {len(df_tratado)} linhas na tabela '{tabela}'.\n")
            return True
        else:
            print(f"  ❌ Falha no inserir_em_lote para a tabela '{tabela}'.\n")
            return False

    except Exception as erro:
        print(f"  ❌ Erro durante a inserção em '{tabela}': {erro}\n")
        return False


def main():
    print("=" * 60)
    print(f"🧪 TESTE DE CARGA RÁPIDA: CAMADA RAW ({LIMITE_LINHAS} LINHAS)")
    print(f"🎯 Banco de Dados: {NOME_BANCO}")
    print("=" * 60 + "\n")

    conexao = conectar(NOME_BANCO)
    if conexao is None:
        print(f"❌ Não foi possível ligar ao banco '{NOME_BANCO}'.")
        sys.exit(1)

    print(f"🔌 Ligado a '{NOME_BANCO}' com sucesso!\n")

    try:
        sucesso_total = True
        for arquivo_csv, cfg in CONFIG_AMOSTRAS.items():
            print(f"📥 Processando amostra de '{arquivo_csv}'...")
            if not testar_amostra(conexao, arquivo_csv, cfg):
                sucesso_total = False
                break

        print("=" * 60)
        if sucesso_total:
            print(f"✅ Teste concluído com sucesso! Todas as tabelas receberam {LIMITE_LINHAS} linhas.")
        else:
            print("❌ O teste apresentou falhas. Verifique as mensagens de erro.")
        print("=" * 60)

    finally:
        conexao.close()
        print("🔒 Conexão com o banco fechada.")


if __name__ == "__main__":
    main()