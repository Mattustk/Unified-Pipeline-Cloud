
# ==============================================================================
# PROJETO: GUILHERME GROUP - PIPELINE DE DADOS UNIFICADA
# DESCRICAO: ETL para processamento e consolidacao de dados das holdings Tech e Retail.
# AUTOR: Guilherme
# NOTA: Todos os dados foram gerados artificialmente pela biblioteca Faker.
# Qualquer semelhanca com a realidade e mera coincidencia.
# ==============================================================================

import pandas as pd
import awswrangler as wr
import boto3 

# ==============================================================================
# 1. CONFIGURAÇÃO DE AMBIENTE (CAMINHOS S3)
# ==============================================================================

# Fontes Raw (Dados Brutos)
BUCKET_RAW_TECH = "s3://guilherme-holding/nexus-tech/raw/tech_nexus.csv"
BUCKET_RAW_RETAIL = "s3://guilherme-holding/nexus-retail/raw/retail_nexus.csv"

# Camada Silver (Dados Processados e Limpos)
BUCKET_OUT_TECH = "s3://guilherme-holding/nexus-tech/processed/"
BUCKET_OUT_RETAIL = "s3://guilherme-holding/nexus-retail/processed/"
BUCKET_OUT_FINAL = "s3://guilherme-holding/guilherme_consolidado/gold_zone/"

# Camada Gold (Visões de Negócio)
BUCKET_GOLD_DIRETORIA = "s3://guilherme-holding/Diretoria/gold/"
BUCKET_GOLD_RH = "s3://guilherme-holding/rh/gold/"
BUCKET_GOLD_FINANCEIRO = "s3://guilherme-holding/financeiro/gold/"

try:
    # ==========================================================================
    # 2. INGESTÃO E LIMPEZA INICIAL
    # ==========================================================================
   
    df_tech = wr.s3.read_csv(path=BUCKET_RAW_TECH)
    df_retail = wr.s3.read_csv(path=BUCKET_RAW_RETAIL)

    # Função interna para tipagem e limpeza rápida
    def clean_base_df(df):
        df['data'] = pd.to_datetime(df['data'])
        cols_numeric = ['quantidade', 'valor_unitario', 'custo_unitario', 'valor_total_transacao']
        for col in cols_numeric:
            df[col] = pd.to_numeric(df[col])
        # Sanitização de CPF (remove caracteres não numéricos)
        df['cpf_cliente'] = df['cpf_cliente'].astype(str).str.replace(r'\D', '', regex=True)
        return df.dropna(subset=['id_transacao', 'valor_total_transacao']).drop_duplicates(subset=['id_transacao'])

    df_tech = clean_base_df(df_tech)
    df_retail = clean_base_df(df_retail)

    # ==========================================================================
    # 3. DATA QUALITY (VALIDAÇÃO CRÍTICA)
    # ==========================================================================
  
    
    # Validação Nexus Tech
    assert df_tech['id_transacao'].isna().sum() == 0, "Falha: ID nulo em Tech"
    assert (df_tech['valor_total_transacao'] > 0).all(), "Falha: Venda negativa em Tech"
    check_tech = (df_tech['valor_unitario'] * df_tech['quantidade']) - df_tech['valor_total_transacao']
    assert (check_tech.abs() < 0.1).all(), "Falha: Divergência matemática em Tech"

    # Validação Nexus Retail
    assert df_retail['id_vendedor'].isna().sum() == 0, "Falha: Vendedor nulo em Retail"
    assert (df_retail['valor_total_transacao'] > 0).all(), "Falha: Venda negativa em Retail"
    check_retail = (df_retail['valor_unitario'] * df_retail['quantidade']) - df_retail['valor_total_transacao']
    assert (check_retail.abs() < 0.1).all(), "Falha: Divergência matemática em Retail"

    # ==========================================================================
    # 4. TRANSFORMAÇÃO E UNIFICAÇÃO (MODELO STAR SCHEMA)
    # ==========================================================================

    df_tech_ready = df_tech.copy()
    df_final = pd.concat([df_tech_ready, df_retail], ignore_index=True)

    # ==========================================================================
    # 5. BUSINESS INTELLIGENCE (AGREGAÇÕES GOLD)
    # ==========================================================================


    # Visão Financeira: Faturamento e Volume Diário
    df_financeiro = df_final.groupby(['data', 'holding']).agg({
        'valor_total_transacao': 'sum',
        'custo_unitario': 'sum', 
        'id_transacao': 'count'
    }).rename(columns={'id_transacao': 'qtd_transacoes', 'valor_total_transacao': 'receita_bruta'}).reset_index()

    # Visão RH: Performance de Vendas e Comissões (5%)
    df_rh = df_final.groupby(['id_vendedor', 'holding']).agg({
        'valor_total_transacao': 'sum',
        'id_transacao': 'count'
    }).rename(columns={'id_transacao': 'total_vendas', 'valor_total_transacao': 'valor_acumulado'}).reset_index()
    df_rh['comissao_a_pagar'] = df_rh['valor_acumulado'] * 0.05

    # Visão Diretoria/Marketing: Produtos mais vendidos
    df_marketing = df_final.groupby(['holding', 'item_vendido']).agg({
        'quantidade': 'sum',
        'valor_total_transacao': 'sum'
    }).sort_values(by='quantidade', ascending=False).reset_index()

    # ==========================================================================
    # 6. PERSISTÊNCIA (STORAGE NO S3 EM PARQUET)
    # ==========================================================================
    
    storage_map = {
        BUCKET_OUT_TECH: df_tech,
        BUCKET_OUT_RETAIL: df_retail,
        BUCKET_OUT_FINAL: df_final,
        BUCKET_GOLD_DIRETORIA: df_marketing,
        BUCKET_GOLD_RH: df_rh,
        BUCKET_GOLD_FINANCEIRO: df_financeiro
    }

    for path, df_target in storage_map.items():
        wr.s3.to_parquet(df=df_target, path=path, dataset=True, mode="overwrite")

except Exception as e:
    print(f" ERRO NO PIPELINE: {e}")
else:
    print(f" WORKFLOW CONCLUÍDO COM SUCESSO!")
