
# ==============================================================================
# PROJETO: GUILHERME GROUP - PIPELINE DE DADOS UNIFICADA
# DESCRICAO: ETL para processamento e consolidacao de dados das holdings Tech e Retail.
# AUTOR: Guilherme
# NOTA: Todos os dados foram gerados artificialmente pela biblioteca Faker.
# Qualquer semelhanca com a realidade e mera coincidencia.
# ==============================================================================

import pandas as pd
import awswrangler as wr # Biblioteca para se conectar com a AWS
import boto3 

# Configuracao dos caminhos do S3
BUCKET_RAW_TECH = 
BUCKET_RAW_RETAIL = 

# Caminhos de destino para os dados processados em formato Parquet
BUCKET_OUT_TECH = 
BUCKET_OUT_RETAIL = 
BUCKET_OUT_FINAL = 

try:
    # ==========================================
    # 1. CARGA DOS DADOS (AGORA VIA S3)
    # ==========================================
    # Leitura dos arquivos brutos diretamente do S3 usando AWS Data Wrangler
    df_tech = wr.s3.read_csv(path=BUCKET_RAW_TECH)
    df_retail = wr.s3.read_csv(path=BUCKET_RAW_RETAIL)

    # ==========================================
    # 2. LIMPEZA E VALIDACAO: DF_TECH
    # ==========================================
    # Conversao de tipos e limpeza de caracteres nao numericos no CPF
    df_tech['data'] = pd.to_datetime(df_tech['data'])
    df_tech['valor'] = pd.to_numeric(df_tech['valor'])
    df_tech['cpf'] = df_tech['cpf'].astype(str).str.replace(r'\D', '', regex=True)

    # Remocao de valores nulos em colunas criticas e eliminacao de duplicatas
    df_tech = df_tech.dropna(subset=['id_transacao', 'holding', 'cpf'])
    df_tech = df_tech.drop_duplicates(subset=['id_transacao'])

    # Validacao de integridade via Asserts para garantir zero valores nulos
    assert df_tech['holding'].isna().sum() == 0, f"Encontrado {df_tech['holding'].isna().sum()} NA em holding"
    assert df_tech['id_transacao'].isna().sum() == 0, f"Encontrado {df_tech['id_transacao'].isna().sum()} NA em id_transacao"
    assert df_tech['id_cliente'].isna().sum() == 0, f"Encontrado {df_tech['id_cliente'].isna().sum()} NA em id_cliente"
    assert df_tech['cpf'].isna().sum() == 0, f"Encontrado {df_tech['cpf'].isna().sum()} NA em cpf"
    assert df_tech['nome_cliente'].isna().sum() == 0, f"Encontrado {df_tech['nome_cliente'].isna().sum()} NA em nome_cliente"
    assert df_tech['email'].isna().sum() == 0, f"Encontrado {df_tech['email'].isna().sum()} NA em email"
    assert df_tech['item_vendido'].isna().sum() == 0, f"Encontrado {df_tech['item_vendido'].isna().sum()} NA em item_vendido"
    assert df_tech['valor'].isna().sum() == 0, f"Encontrado {df_tech['valor'].isna().sum()} NA em valor"
    assert df_tech['data'].isna().sum() == 0, f"Encontrado {df_tech['data'].isna().sum()} NA em data"

    # ==========================================
    # 3. LIMPEZA E VALIDACAO: DF_RETAIL
    # ==========================================
    # Processo de limpeza similar aplicado aos dados de Retail
    df_retail['cpf'] = df_retail['cpf'].astype(str).str.replace(r'\D', '', regex=True)
    df_retail['data'] = pd.to_datetime(df_retail['data'])
    df_retail['valor'] = pd.to_numeric(df_retail['valor'])

    df_retail = df_retail.dropna(subset=['id_venda'])
    df_retail = df_retail.drop_duplicates(subset=['id_venda'])

    assert df_retail['holding'].isna().sum() == 0, f"Encontrado {df_retail['holding'].isna().sum()} NA em holding"
    assert df_retail['id_venda'].isna().sum() == 0, f"Encontrado {df_retail['id_venda'].isna().sum()} NA em id_venda"
    assert df_retail['id_cliente'].isna().sum() == 0, f"Encontrado {df_retail['id_cliente'].isna().sum()} NA em id_cliente"
    assert df_retail['cpf'].isna().sum() == 0, f"Encontrado {df_retail['cpf'].isna().sum()} NA em cpf"
    assert df_retail['nome_cliente'].isna().sum() == 0, f"Encontrado {df_retail['nome_cliente'].isna().sum()} NA em nome_cliente"
    assert df_retail['email'].isna().sum() == 0, f"Encontrado {df_retail['email'].isna().sum()} NA em email"
    assert df_retail['item_vendido'].isna().sum() == 0, f"Encontrado {df_retail['item_vendido'].isna().sum()} NA em item_vendido"
    assert df_retail['valor'].isna().sum() == 0, f"Encontrado {df_retail['valor'].isna().sum()} NA em valor"
    assert df_retail['data'].isna().sum() == 0, f"Encontrado {df_retail['data'].isna().sum()} NA em data"

    # ==========================================
    # 4. UNIFICACAO DA HOLDING
    # ==========================================
    # Padronizacao de nomes de colunas para unificacao dos DataFrames
    df_tech_ready = df_tech.rename(columns={'id_transacao': 'id_venda'})
    df_retail_ready = df_retail.copy() 

    # Consolidacao final dos dados tratados
    df_final = pd.concat([df_tech_ready, df_retail_ready], ignore_index=True)

    # ==========================================
    # 5. CHECK FINAL E SALVAMENTO NO S3
    # ==========================================
    # Ultima camada de seguranca antes da carga final
    assert df_final['id_cliente'].isna().sum() == 0, "O processo gerou dados nulos em id_cliente"
    assert df_final['valor'].isna().sum() == 0, "O processo gerou dados nulos em valor"

    # Salvamento dos dados em formato Parquet com modo overwrite para evitar duplicidade
    wr.s3.to_parquet(df=df_tech, path=BUCKET_OUT_TECH, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_retail, path=BUCKET_OUT_RETAIL, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_final, path=BUCKET_OUT_FINAL, dataset=True, mode="overwrite")

# Tratamento de excecoes para erros de validacao ou problemas de conexao AWS
except Exception as e:
    if isinstance(e, AssertionError):
        print(f"ALERTA DE DADO SUJO: {e}")
    else:
        print(f"ERRO NA CONEXAO OU PROCESSAMENTO AWS: {e}")

else:
    print(f"WORKFLOW CONCLUIDO! Dados salvos nos 3 buckets S3 com overwrite.")
