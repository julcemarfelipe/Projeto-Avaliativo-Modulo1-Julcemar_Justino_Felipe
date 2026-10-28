import sys
from banco import conectar, executar
from sqlalchemy.exc import SQLAlchemyError

NOME_BANCO = "viagens_transparencia"

print("=" * 60)
print("🚀 FASE 2: TRANSFORMAR DADOS PARA A CAMADA SILVER")
print(f"🎯 Banco de Dados: {NOME_BANCO}")
print("=" * 60 + "\n")

conexao = conectar(NOME_BANCO)

if conexao is None:
    print(f"❌ Não foi possível conectar ao banco '{NOME_BANCO}'. Verifique suas credenciais.")
    sys.exit(1)

try:
    # =========================================================================
    # PASSO 0: LIMPAR TABELAS SILVER (Filhas primeiro por causa das FKs)
    # =========================================================================
    print("🧹 [Passo 0] Limpando tabelas silver (ordem inversa de dependência)...")
    executar(conexao, "DELETE FROM silver_trechos", commit=False)
    executar(conexao, "DELETE FROM silver_passagens", commit=False)
    executar(conexao, "DELETE FROM silver_pagamentos", commit=False)
    executar(conexao, "DELETE FROM silver_viagens", commit=False)
    print("   ✓ Tabelas silver limpas com sucesso.")

    # =========================================================================
    # PASSO 1: INSERIR VIAGENS (Tabela Pai)
    # Deduplicação por id_viagem, tratamento de datas e valores decimais
    # =========================================================================
    print("\n📥 [Passo 1/6] Inserindo dados na tabela 'silver_viagens'...")
    sql_viagens = """
    INSERT INTO silver_viagens (
        id_viagem,
        num_proposta,
        situacao,
        viagem_urgente,
        cod_orgao_superior,
        nome_orgao_superior,
        nome_viajante,
        cargo,
        data_inicio,
        data_fim,
        destinos,
        motivo,
        valor_diarias,
        valor_passagens,
        valor_devolucao,
        valor_outros_gastos
    )
    SELECT DISTINCT ON (TRIM(id_viagem))
        TRIM(id_viagem),
        TRIM(num_proposta),
        TRIM(situacao),
        TRIM(viagem_urgente),
        TRIM(cod_orgao_superior),
        COALESCE(NULLIF(TRIM(nome_orgao_superior), ''), 'Não informado'),
        TRIM(nome_viajante),
        TRIM(cargo),
        CASE 
            WHEN TRIM(data_inicio) ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' 
            THEN TO_DATE(TRIM(data_inicio), 'DD/MM/YYYY') 
            ELSE NULL 
        END,
        CASE 
            WHEN TRIM(data_fim) ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' 
            THEN TO_DATE(TRIM(data_fim), 'DD/MM/YYYY') 
            ELSE NULL 
        END,
        LEFT(TRIM(destinos), 4000),
        LEFT(TRIM(motivo), 4000),
        CASE 
            WHEN TRIM(valor_diarias) = '' OR valor_diarias IS NULL THEN 0.00
            ELSE GREATEST(0.00, CAST(REPLACE(REPLACE(TRIM(valor_diarias), '.', ''), ',', '.') AS DECIMAL(10,2)))
        END,
        CASE 
            WHEN TRIM(valor_passagens) = '' OR valor_passagens IS NULL THEN 0.00
            ELSE CAST(REPLACE(REPLACE(TRIM(valor_passagens), '.', ''), ',', '.') AS DECIMAL(10,2))
        END,
        CASE 
            WHEN TRIM(valor_devolucao) = '' OR valor_devolucao IS NULL THEN 0.00
            ELSE CAST(REPLACE(REPLACE(TRIM(valor_devolucao), '.', ''), ',', '.') AS DECIMAL(10,2))
        END,
        CASE 
            WHEN TRIM(valor_outros_gastos) = '' OR valor_outros_gastos IS NULL THEN 0.00
            ELSE CAST(REPLACE(REPLACE(TRIM(valor_outros_gastos), '.', ''), ',', '.') AS DECIMAL(10,2))
        END
    FROM raw_viagens
    WHERE TRIM(id_viagem) IS NOT NULL AND TRIM(id_viagem) <> ''
    ORDER BY TRIM(id_viagem);
    """
    executar(conexao, sql_viagens, commit=False)
    print("   ✓ Registros inseridos em 'silver_viagens'.")

    # =========================================================================
    # PASSO 2: CALCULAR COLUNAS valor_total E duracao_dias EM silver_viagens
    # Fórmula: valor_total = diárias + passagens + outros_gastos - devolução
    # duracao_dias = (data_fim - data_inicio) + 1
    # =========================================================================
    print("\n⚙️  [Passo 2/6] Calculando 'valor_total' e 'duracao_dias' em silver_viagens...")
    sql_calc_viagens = """
    UPDATE silver_viagens
    SET 
        valor_total = COALESCE(valor_diarias, 0::numeric) 
                    + COALESCE(valor_passagens, 0::numeric) 
                    + COALESCE(valor_outros_gastos, 0::numeric) 
                    - COALESCE(valor_devolucao, 0::numeric),
        duracao_dias = CASE 
            WHEN data_inicio IS NOT NULL AND data_fim IS NOT NULL 
            THEN GREATEST(0, (data_fim - data_inicio) + 1)
            ELSE 0
        END;
    """
    executar(conexao, sql_calc_viagens, commit=False)
    print("   ✓ Colunas calculadas atualizadas em 'silver_viagens'.")

    # =========================================================================
    # PASSO 3: INSERIR PAGAMENTOS (Tabela Filha com FK em silver_viagens)
    # Garante integridade referencial (INNER JOIN com silver_viagens)
    # =========================================================================
    print("\n📥 [Passo 3/6] Inserindo dados em 'silver_pagamentos' (respeitando FK)...")
    sql_pagamentos = """
    INSERT INTO silver_pagamentos (
        id_viagem,
        num_proposta,
        nome_orgao_pagador,
        nome_ug_pagadora,
        tipo_pagamento,
        valor
    )
    SELECT
        sv.id_viagem,
        TRIM(rp.num_proposta),
        TRIM(rp.nome_orgao_pagador),
        TRIM(rp.nome_ug_pagadora),
        COALESCE(NULLIF(TRIM(rp.tipo_pagamento), ''), 'Não informado'),
        CASE 
            WHEN TRIM(rp.valor) = '' OR rp.valor IS NULL THEN 0.00
            ELSE GREATEST(0.00, CAST(REPLACE(REPLACE(TRIM(rp.valor), '.', ''), ',', '.') AS NUMERIC(10,2)))
        END
    FROM raw_pagamentos rp
    INNER JOIN silver_viagens sv 
        ON sv.id_viagem = TRIM(rp.id_viagem);
    """
    executar(conexao, sql_pagamentos, commit=False)
    print("   ✓ Registros inseridos em 'silver_pagamentos'.")

    # =========================================================================
    # PASSO 4: INSERIR PASSAGENS (Tabela Filha com FK em silver_viagens)
    # =========================================================================
    print("\n📥 [Passo 4/6] Inserindo dados em 'silver_passagens' (respeitando FK)...")
    sql_passagens = """
    INSERT INTO silver_passagens (
        id_viagem,
        meio_transporte,
        pais_origem_ida,
        uf_origem_ida,
        cidade_origem_ida,
        pais_destino_ida,
        uf_destino_ida,
        cidade_destino_ida,
        valor_passagem,
        taxa_servico,
        data_emissao
    )
    SELECT
        sv.id_viagem,
        TRIM(rp.meio_transporte),
        TRIM(rp.pais_origem_ida),
        TRIM(rp.uf_origem_ida),
        TRIM(rp.cidade_origem_ida),
        TRIM(rp.pais_destino_ida),
        TRIM(rp.uf_destino_ida),
        TRIM(rp.cidade_destino_ida),
        CASE 
            WHEN TRIM(rp.valor_passagem) = '' OR rp.valor_passagem IS NULL THEN 0.00
            ELSE GREATEST(0.00, CAST(REPLACE(REPLACE(TRIM(rp.valor_passagem), '.', ''), ',', '.') AS NUMERIC(10,2)))
        END,
        CASE 
            WHEN TRIM(rp.taxa_servico) = '' OR rp.taxa_servico IS NULL THEN 0.00
            ELSE GREATEST(0.00, CAST(REPLACE(REPLACE(TRIM(rp.taxa_servico), '.', ''), ',', '.') AS NUMERIC(10,2)))
        END,
        CASE 
            WHEN TRIM(rp.data_emissao_compra) ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' 
            THEN TO_DATE(TRIM(rp.data_emissao_compra), 'DD/MM/YYYY') 
            ELSE NULL 
        END
    FROM raw_passagens rp
    INNER JOIN silver_viagens sv 
        ON sv.id_viagem = TRIM(rp.id_processo_viagem);
    """
    executar(conexao, sql_passagens, commit=False)
    print("   ✓ Registros inseridos em 'silver_passagens'.")

    # =========================================================================
    # PASSO 5: INSERIR TRECHOS (Tabela Filha com FK e Deduplicação UNIQUE)
    # Garante que não repete (id_viagem, sequencia_trecho)
    # =========================================================================
    print("\n📥 [Passo 5/6] Inserindo dados em 'silver_trechos' (respeitando FK)...")
    sql_trechos = """
    INSERT INTO silver_trechos (
        id_viagem,
        sequencia_trecho,
        origem_data,
        origem_uf,
        origem_cidade,
        destino_data,
        destino_uf,
        destino_cidade,
        meio_transporte,
        numero_diarias
    )
    SELECT DISTINCT ON (sv.id_viagem, CAST(NULLIF(REGEXP_REPLACE(TRIM(rt.sequencia_trecho), '[^0-9]', '', 'g'), '') AS INT))
        sv.id_viagem,
        CAST(NULLIF(REGEXP_REPLACE(TRIM(rt.sequencia_trecho), '[^0-9]', '', 'g'), '') AS INT),
        CASE 
            WHEN TRIM(rt.origem_data) ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' 
            THEN TO_DATE(TRIM(rt.origem_data), 'DD/MM/YYYY') 
            ELSE NULL 
        END,
        TRIM(rt.origem_uf),
        TRIM(rt.origem_cidade),
        CASE 
            WHEN TRIM(rt.destino_data) ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' 
            THEN TO_DATE(TRIM(rt.destino_data), 'DD/MM/YYYY') 
            ELSE NULL 
        END,
        TRIM(rt.destino_uf),
        TRIM(rt.destino_cidade),
        TRIM(rt.meio_transporte),
        CASE 
            WHEN TRIM(rt.numero_diarias) = '' OR rt.numero_diarias IS NULL THEN 0.00
            ELSE GREATEST(0.00, CAST(REPLACE(REPLACE(TRIM(rt.numero_diarias), '.', ''), ',', '.') AS NUMERIC(10,2)))
        END
    FROM raw_trechos rt
    INNER JOIN silver_viagens sv 
        ON sv.id_viagem = TRIM(rt.id_processo_viagem)
    WHERE NULLIF(REGEXP_REPLACE(TRIM(rt.sequencia_trecho), '[^0-9]', '', 'g'), '') IS NOT NULL
    ORDER BY sv.id_viagem, CAST(NULLIF(REGEXP_REPLACE(TRIM(rt.sequencia_trecho), '[^0-9]', '', 'g'), '') AS INT);
    """
    executar(conexao, sql_trechos, commit=False)
    print("   ✓ Registros inseridos em 'silver_trechos'.")

    # =========================================================================
    # PASSO 6: COMMIT GERAL DA TRANSAÇÃO
    # =========================================================================
    print("\n🔒 [Passo 6/6] Confirmando transação completa no banco...")
    conexao.commit()

    print("\n" + "=" * 60)
    print("✅ Fase 2 concluída com sucesso! Camada Silver populada e consistente.")
    print("=" * 60)

except SQLAlchemyError as e:
    print(f"\n❌ Erro durante a transformação para a camada Silver: {e}")
    print("   Revertendo mudanças (ROLLBACK)...")
    conexao.rollback()
    sys.exit(1)
finally:
    conexao.close()
    print("🔒 Conexão com o banco fechada.")