from banco import conectar, executar
from sqlalchemy.exc import SQLAlchemyError

print("=" * 60)
print("FASE 2: TRANSFORMAR DADOS PARA SILVER")
print("=" * 60 + "\n")

conexao = conectar('cafeteria')

if conexao is None:
    print("❌ Não foi possível conectar ao banco")
    exit(1)

try:
    print("→ Limpando tabelas silver (filha primeiro)...")
    executar(conexao, "DELETE FROM silver_itens", commit=False)
    executar(conexao, "DELETE FROM silver_vendas", commit=False)
    
    # ===== PASSO 1: INSERIR VENDAS =====
    print("→ Inserindo dados em silver_vendas...")
    sql_vendas = """
    INSERT INTO silver_vendas (
        id_venda, data_pedido, data_entrega, nome_loja, 
        id_cliente, valor_bruto, valor_desconto
    )
    SELECT
        CAST(REPLACE(TRIM(id_venda), 'V', '') AS INTEGER),
        TO_DATE(TRIM(data_pedido), 'DD/MM/YYYY'),
        TO_DATE(TRIM(data_entrega), 'DD/MM/YYYY'),
        TRIM(nome_loja),
        CASE WHEN TRIM(id_cliente) = '' THEN NULL ELSE CAST(REPLACE(TRIM(id_cliente), 'C', '') AS INTEGER) END,
        CASE WHEN TRIM(valor_bruto) = '' THEN NULL 
             ELSE CAST(REPLACE(REPLACE(TRIM(valor_bruto), '.', ''), ',', '.') AS NUMERIC(10,2)) END,
        CASE WHEN TRIM(valor_desconto) = '' THEN NULL 
             ELSE CAST(REPLACE(REPLACE(TRIM(valor_desconto), '.', ''), ',', '.') AS NUMERIC(10,2)) END
    FROM raw_vendas
    """
    executar(conexao, sql_vendas, commit=False)
    
    # ===== PASSO 2: CALCULAR valor_total E prazo_dias =====
    print("→ Calculando valor_total e prazo_dias...")
    sql_calc_vendas = """
    UPDATE silver_vendas SET
    valor_total = COALESCE(valor_bruto, 0::numeric)
                 - COALESCE(valor_desconto, 0::numeric),
    prazo_dias = (data_entrega - data_pedido);
        """
    executar(conexao, sql_calc_vendas, commit=False)
    
    # ===== PASSO 3: INSERIR ITENS =====
    print("→ Inserindo dados em silver_itens...")
    sql_itens = """
    
    INSERT INTO silver_itens (
    id_venda,
    sequencia_item,
    produto,
    categoria,
    quantidade,
    preco_unitario
)
SELECT
    CAST(REPLACE(TRIM(ri.id_venda), 'V', '') AS INTEGER),
    CAST(TRIM(ri.sequencia_item) AS INTEGER),
    TRIM(ri.produto),
    TRIM(ri.categoria),
    CAST(TRIM(ri.quantidade) AS INTEGER),
    CAST(
        REPLACE(
            REPLACE(TRIM(ri.preco_unitario), '.', ''),
            ',', '.'
        ) AS NUMERIC(10,2)
    )
FROM raw_itens ri
INNER JOIN silver_vendas sv
    ON sv.id_venda =
       CAST(REPLACE(TRIM(ri.id_venda), 'V', '') AS INTEGER);
    """
    executar(conexao, sql_itens, commit=False)
    
    # ===== PASSO 4: CALCULAR subtotal =====
    print("→ Calculando subtotal dos itens...")
    sql_calc_itens = """
    UPDATE silver_itens SET
        subtotal = quantidade * preco_unitario
    """
    executar(conexao, sql_calc_itens, commit=False)
    
    # ===== PASSO 5: COMMIT (CONFIRMA TUDO) =====
    print("→ Confirmando transação...")
    conexao.commit()
    
    print("\n✅ Fase 2 concluída com sucesso!")
    print("=" * 60)
    
except SQLAlchemyError as e:
    print(f"\n❌ Erro durante transformação: {e}")
    print("   Revertendo mudanças...")
    conexao.rollback()
    exit(1)
finally:
    conexao.close()