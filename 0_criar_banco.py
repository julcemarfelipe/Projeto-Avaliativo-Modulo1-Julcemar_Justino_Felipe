import re
from banco import motor
from sqlalchemy import text

SQL_FILE = '0_criar_banco.sql'
DB_NOME = 'viagens_transparencia'

print("=" * 60)
print("🚀 [Fase 0] Inicialização do Banco de Dados e Modelagem")
print("=" * 60)

# -------------------------------------------------------------
# 1. Leitura do arquivo SQL
# -------------------------------------------------------------
print(f"\n📄 [Passo 1/4] Lendo o arquivo '{SQL_FILE}'...")
try:
    with open(SQL_FILE, 'r', encoding='latin-1') as arquivo:
        sql_content = arquivo.read()
    print("✓ Arquivo SQL carregado com sucesso.")
except FileNotFoundError:
    print(f"❌ Erro: Arquivo '{SQL_FILE}' não foi encontrado na raiz do projeto.")
    exit(1)

# -------------------------------------------------------------
# 2. Conectar ao PostgreSQL padrão ('postgres') e recriar database
# -------------------------------------------------------------
print(f"\n🔌 [Passo 2/4] Conectando ao PostgreSQL padrão para recriar '{DB_NOME}'...")
engine_padrao = motor('postgres')

if engine_padrao is None:
    print("❌ Falha na conexão padrão. Verifique as credenciais no seu arquivo .env")
    exit(1)

print("✓ Conectado ao PostgreSQL padrão.")

conn_raw = engine_padrao.raw_connection()
conn_raw.set_isolation_level(0)  # AUTOCOMMIT necessário para CREATE/DROP DATABASE
cursor = conn_raw.cursor()

try:
    print("   ↳ Encerrando sessões ativas na base de dados...")
    cursor.execute(f"""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{DB_NOME}'
        AND pid <> pg_backend_pid();
    """)

    print(f"   ↳ Recriando banco '{DB_NOME}' com encoding UTF-8...")
    cursor.execute(f"DROP DATABASE IF EXISTS {DB_NOME};")
    cursor.execute(f"CREATE DATABASE {DB_NOME} ENCODING 'UTF8';")
    print(f"✓ Base de dados '{DB_NOME}' criada com sucesso!")

except Exception as erro:
    print(f"❌ Erro ao recriar a base de dados: {erro}")
    exit(1)
finally:
    cursor.close()
    conn_raw.close()
    engine_padrao.dispose()

# -------------------------------------------------------------
# 3. Conectar ao banco criado e executar as DDLs com log detalhado
# -------------------------------------------------------------
print(f"\n⚙️  [Passo 3/4] Conectando a '{DB_NOME}' e criando tabelas...")
engine_viagens = motor(DB_NOME)

if engine_viagens is None:
    print(f"❌ Falha ao conectar na nova base '{DB_NOME}'.")
    exit(1)

# Divide os comandos por ponto e vírgula
comandos = sql_content.split(';')

with engine_viagens.connect() as conexao:
    transacao = conexao.begin()
    try:
        total_comandos = 0
        for cmd in comandos:
            cmd_limpo = cmd.strip()
            # Ignora comandos vazios ou apenas comentários
            if not cmd_limpo or cmd_limpo.startswith('--'):
                continue

            # Detecta nome da tabela em comandos CREATE TABLE
            match_tabela = re.search(
                r'create\s+table\s+(?:if\s+not\s+exists\s+)?([a-zA-Z0-9_]+)',
                cmd_limpo,
                re.IGNORECASE
            )

            if match_tabela:
                nome_tabela = match_tabela.group(1).lower()
                if nome_tabela.startswith('raw_'):
                    print(f"   📥 [Raw] Criando tabela bruta: {nome_tabela}...")
                elif nome_tabela.startswith('silver_'):
                    print(f"   🥈 [Silver] Criando tabela modelada: {nome_tabela}...")
                else:
                    print(f"   📋 Criando tabela: {nome_tabela}...")

            conexao.execute(text(cmd_limpo))
            total_comandos += 1

        transacao.commit()
        print(f"\n✓ {total_comandos} comando(s) DDL executados com sucesso.")

    except Exception as erro:
        transacao.rollback()
        print(f"\n❌ Erro durante a criação das tabelas: {erro}")
        exit(1)

# -------------------------------------------------------------
# 4. Auditoria e Validação Final das Tabelas Criadas
# -------------------------------------------------------------
print("\n🔍 [Passo 4/4] Validando tabelas registradas no PostgreSQL...")
with engine_viagens.connect() as conexao:
    resultado = conexao.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """))
    tabelas_existentes = [linha[0] for linha in resultado]

tabelas_raw = [t for t in tabelas_existentes if t.startswith('raw_')]
tabelas_silver = [t for t in tabelas_existentes if t.startswith('silver_')]

print("\n--- Relatório de Criação ---")
print(f"📥 Camada Raw ({len(tabelas_raw)} tabelas):")
for t in tabelas_raw:
    print(f"   ✔ {t}")

print(f"\n🥈 Camada Silver ({len(tabelas_silver)} tabelas):")
for t in tabelas_silver:
    print(f"   ✔ {t}")

if len(tabelas_raw) == 4 and len(tabelas_silver) == 4:
    print("\n" + "=" * 60)
    print("✅ Fase 0 concluída com sucesso! Todas as 8 tabelas foram criadas.")
    print("=" * 60)
else:
    print(f"\n⚠️  Atenção: Esperadas 8 tabelas (4 Raw e 4 Silver), mas foram encontradas {len(tabelas_existentes)}.")