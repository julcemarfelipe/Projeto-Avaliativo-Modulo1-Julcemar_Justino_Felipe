-- =====================================================================
-- Criação do banco de dados e tabelas para o pipeline viagens_transparencia
-- =====================================================================

-- DROP DATABASE IF EXISTS viagens_transparencia;
-- CREATE DATABASE viagens_transparencia ENCODING 'latin1';

-- =====================================================================
-- TABELAS RAW (dados brutos do CSV, tudo como texto)
-- =====================================================================

DROP TABLE IF EXISTS raw_viagens CASCADE;
DROP TABLE IF EXISTS raw_trechos CASCADE;
DROP TABLE IF EXISTS raw_passagens CASCADE;
DROP TABLE IF EXISTS raw_pagamentos CASCADE;


CREATE TABLE raw_viagens (
    id_viagem VARCHAR(20),
    num_proposta VARCHAR(20),
    situacao VARCHAR(50),
    viagem_urgente VARCHAR(5),
    cod_orgao_superior VARCHAR(20),
    nome_orgao_superior VARCHAR(255),
    nome_viajante VARCHAR(255),
    cargo VARCHAR(255),
    data_inicio VARCHAR(10),
    data_fim VARCHAR(10),
    destinos VARCHAR(4000),
    motivo VARCHAR(4000),
    valor_diarias VARCHAR(20),
    valor_passagens VARCHAR(20),
    valor_devolucao VARCHAR(20),
    valor_outros_gastos VARCHAR(20)
);


CREATE TABLE raw_passagens (
    id_passagem VARCHAR(20),
    id_viagem VARCHAR(20),
    meio_transporte VARCHAR(50),
    pais_origem_ida VARCHAR(60),
    uf_origem_ida VARCHAR(40),
    cidade_origem_ida VARCHAR(80),
    pais_destino_ida VARCHAR(60),
    uf_destino_ida VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem VARCHAR(20),
    taxa_servico VARCHAR(20),
    data_emissao VARCHAR(10)
);

CREATE TABLE raw_pagamentos (
    id_pagamento VARCHAR(20),
    id_viagem VARCHAR(20),
    num_proposta VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora VARCHAR(255),
    tipo_pagamento VARCHAR(50),
    valor VARCHAR(20)
);


CREATE TABLE raw_trechos (
    id_trecho VARCHAR(20),
    id_viagem VARCHAR(20),
    sequencia_trecho VARCHAR(10),
    origem_data VARCHAR(10),
    origem_uf VARCHAR(40),
    origem_cidade VARCHAR(80),
    destino_data VARCHAR(10),
    destino_uf VARCHAR(40),
    destino_cidade VARCHAR(80),
    meio_transporte VARCHAR(50),
    numero_diarias VARCHAR(20)
);

-- =====================================================================
-- TABELAS SILVER (dados limpos e convertidos para tipos corretos)
-- =====================================================================

DROP TABLE IF EXISTS silver_itens CASCADE;
DROP TABLE IF EXISTS silver_vendas CASCADE;

DROP TABLE IF EXISTS silver_viagens CASCADE;

CREATE TABLE silver_viagens (
    id_viagem VARCHAR(20) PRIMARY KEY NOT NULL,
    num_proposta VARCHAR(20),
    situacao VARCHAR(50),
    viagem_urgente VARCHAR(5),
    cod_orgao_superior VARCHAR(20),
    nome_orgao_superior VARCHAR(255) NOT NULL,
    nome_viajante VARCHAR(255),
    cargo VARCHAR(255),
    data_inicio DATE,
    data_fim DATE,
    destinos VARCHAR(4000),
    motivo VARCHAR(4000),
    valor_diarias DECIMAL(10,2) CHECK (valor_diarias >= 0),
    valor_passagens DECIMAL(10,2),
    valor_devolucao DECIMAL(10,2),
    valor_outros_gastos DECIMAL(10,2),
    valor_total DECIMAL(12,2),
    duracao_dias INT
);


CREATE TABLE silver_passagens (
    id_passagem SERIAL PRIMARY KEY,
    id_viagem VARCHAR(20) NOT NULL,
    meio_transporte VARCHAR(50),
    pais_origem_ida VARCHAR(60),
    uf_origem_ida VARCHAR(40),
    cidade_origem_ida VARCHAR(80),
    pais_destino_ida VARCHAR(60),
    uf_destino_ida VARCHAR(40),
    cidade_destino_ida VARCHAR(80),
    valor_passagem NUMERIC(10,2) CHECK (valor_passagem >= 0),
    taxa_servico NUMERIC(10,2) CHECK (taxa_servico >= 0),
    data_emissao DATE,
    FOREIGN KEY (id_viagem) REFERENCES silver_viagens(id_viagem)
);

CREATE TABLE silver_pagamentos (
    id_pagamento SERIAL PRIMARY KEY,
    id_viagem VARCHAR(20) NOT NULL,
    num_proposta VARCHAR(20),
    nome_orgao_pagador VARCHAR(255),
    nome_ug_pagadora VARCHAR(255),
    tipo_pagamento VARCHAR(50) NOT NULL,
    valor NUMERIC(10,2) CHECK (valor >= 0),
    FOREIGN KEY (id_viagem)
        REFERENCES silver_viagens(id_viagem)
);

CREATE TABLE silver_trechos (
    id_trecho SERIAL PRIMARY KEY,
    id_viagem VARCHAR(20) NOT NULL,
    sequencia_trecho INT,
    origem_data DATE,
    origem_uf VARCHAR(40),
    origem_cidade VARCHAR(80),
    destino_data DATE,
    destino_uf VARCHAR(40),
    destino_cidade VARCHAR(80),
    meio_transporte VARCHAR(50),
    numero_diarias NUMERIC(10,2) CHECK (numero_diarias >= 0),
    FOREIGN KEY (id_viagem)
        REFERENCES silver_viagens(id_viagem)
);