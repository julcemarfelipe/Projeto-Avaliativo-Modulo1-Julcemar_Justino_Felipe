from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config import POSTGRES_CONFIG
import pandas as pd


def motor(dbname=None):
    """
    Cria uma conexão SQLAlchemy com o PostgreSQL.

    Args:
        dbname: Nome do banco. Se None, conecta ao banco 'postgres' (padrão).

    Returns:
        engine: Objeto SQLAlchemy Engine.
    """
    if dbname is None:
        dbname = 'postgres'  # Banco padrão do PostgreSQL

    url = (
        f"postgresql+psycopg2://"
        f"{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
        f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{dbname}"
    )

    try:
        engine = create_engine(url)
        return engine
    except Exception as e:
        print(f"Erro ao criar engine: {e}")
        return None


def conectar(dbname='viagens_transparencia'):
    """
    Abre uma conexão com o PostgreSQL e retorna o objeto Connection.

    Args:
        dbname: Nome do banco (padrão: 'viagens_transparencia').

    Returns:
        Connection: Conexão aberta, ou None se falhar.
    """
    try:
        engine = motor(dbname)
        conexao = engine.connect()
        return conexao
    except SQLAlchemyError as e:
        print(f"❌ Erro ao conectar ao PostgreSQL:")
        print(f"   Host: {POSTGRES_CONFIG['host']}")
        print(f"   Porta: {POSTGRES_CONFIG['port']}")
        print(f"   Usuário: {POSTGRES_CONFIG['user']}")
        print(f"   Banco: {dbname}")
        print(f"   Mensagem: {e.orig}")
        return None


def executar(conexao, sql, commit=True):
    """
    Executa um comando SQL (INSERT, DELETE, UPDATE, CREATE, etc.).

    Args:
        conexao: Objeto Connection aberto.
        sql: String com o SQL a executar.
        commit: Se True, faz commit automático. Se False, precisa fazer commit manualmente.

    Returns:
        True se sucesso, False se erro.
    """
    try:
        conexao.execute(text(sql))
        if commit:
            conexao.commit()
        return True
    except SQLAlchemyError as e:
        print(f"❌ Erro ao executar SQL: {e.orig}")
        conexao.rollback()
        return False


def consultar(sql, conexao):
    """
    Executa uma query SELECT e retorna os resultados em um DataFrame pandas.

    Args:
        sql: String com a query SELECT.
        conexao: Objeto Connection aberto.

    Returns:
        DataFrame com os resultados.
    """
    try:
        df = pd.read_sql(text(sql), conexao, coerce_float=True)
        return df
    except SQLAlchemyError as e:
        print(f"❌ Erro ao consultar: {e.orig}")
        return None


def inserir_em_lote(conexao, tabela, dataframe):
    """
    Insere um DataFrame inteiro em uma tabela, em lotes de 1000 linhas.

    Args:
        conexao: Objeto Connection aberto.
        tabela: Nome da tabela.
        dataframe: DataFrame a inserir.

    Returns:
        True se sucesso, False se erro.
    """
    try:
        dataframe.to_sql(
            tabela,
            conexao,
            if_exists='append',
            method='multi',
            chunksize=1000,
            index=False
        )
        conexao.commit()
        return True
    except SQLAlchemyError as e:
        print(f"❌ Erro ao inserir em lote: {e.orig}")
        conexao.rollback()
        return False
