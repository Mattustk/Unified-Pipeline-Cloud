
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
import logging
from datetime import datetime

# 1. ENGENHARIA DE SOFTWARE: LOGGING ESTRUTURADO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MirantePipeline")

# Configurações de Caminho
BUCKET_BASE = "___________"
PATHS = {
    "raw_tech": f"{BUCKET_BASE}___________",
    "raw_retail": f"{BUCKET_BASE}___________",
    "quarantine": f"{BUCKET_BASE}___________",
    "silver_tech": f"{BUCKET_BASE}___________",
    "silver_retail": f"{BUCKET_BASE}___________",
    "gold_financeiro": f"{BUCKET_BASE}___________",
    "gold_rh": f"{BUCKET_BASE}___________",
    "gold_consolidado": f"{BUCKET_BASE}___________" # <--- Caminho ajustado
}

# 2. FINANÇAS: ADR para Comissões
TAXA_COMISSAO = 0.01 

def validate_data_quality(df, context):
    """Implementa Quality Gates. Retorna (df_clean, df_quarantine)"""
    # Check 1: Integridade Financeira
    df['check_total'] = abs((df['valor_unitario'] * df['quantidade']) - df['valor_total_transacao'])
    mask_check_financeiro = df['check_total'] > 0.01 
    
    # Check 2: Integridade de IDs e Valores
    mask_inconsistente = (
        df['id_transacao'].isna() | 
        (df['valor_total_transacao'] <= 0) | 
        mask_check_financeiro
    )
    
    df_quarantine = df[mask_inconsistente].copy()
    df_quarantine['motivo_rejeicao'] = "Inconsistência Financeira ou ID ausente"
    
    df_clean = df[~mask_inconsistente].drop(columns=['check_total'])
    
    if not df_quarantine.empty:
        logger.warning(f" {context}: {len(df_quarantine)} registros enviados para QUARENTENA.")
        wr.s3.to_csv(df_quarantine, path=PATHS['quarantine'], dataset=True, mode="append", index=False)
        
    return df_clean

try:
    logger.info("--- INICIANDO WORKFLOW V2.0 (PADRÃO MIRANTE) ---")

    # 3. INGESTÃO BRONZE (Schema Enforcement)
    df_tech_raw = wr.s3.read_csv(path=PATHS['raw_tech'], dtype=str)
    df_retail_raw = wr.s3.read_csv(path=PATHS['raw_retail'], dtype=str)

    for df in [df_tech_raw, df_retail_raw]:
        df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
        df['valor_total_transacao'] = pd.to_numeric(df['valor_total_transacao'], errors='coerce')
        df['custo_unitario'] = pd.to_numeric(df['custo_unitario'], errors='coerce')
        df['data'] = pd.to_datetime(df['data'], errors='coerce')

    # 4. SILVER LAYER: HIGIENIZAÇÃO
    df_tech_silver = validate_data_quality(df_tech_raw, "NEXUS_TECH")
    df_retail_silver = validate_data_quality(df_retail_raw, "NEXUS_RETAIL")

    wr.s3.to_parquet(df_tech_silver, path=PATHS['silver_tech'], dataset=True, mode="overwrite")
    wr.s3.to_parquet(df_retail_silver, path=PATHS['silver_retail'], dataset=True, mode="overwrite")

    # 5. GOLD LAYER: BUSINESS LOGIC
    df_gold = pd.concat([df_tech_silver, df_retail_silver], ignore_index=True)
    
    # Gold RH
    df_rh = df_gold.groupby(['id_vendedor', 'holding']).agg({
        'valor_total_transacao': 'sum', 'id_transacao': 'count'
    }).rename(columns={'id_transacao': 'total_vendas', 'valor_total_transacao': 'venda_bruta'}).reset_index()
    df_rh['comissao_valor'] = df_rh['venda_bruta'] * TAXA_COMISSAO

    # Gold Financeiro
    df_financeiro = df_gold.groupby(['data', 'holding']).agg({
        'valor_total_transacao': 'sum', 'custo_unitario': 'sum'
    }).reset_index()

    # SALVAMENTOS FINAIS
    wr.s3.to_csv(df_rh, path=PATHS['gold_rh'], dataset=True, mode="overwrite", index=False)
    wr.s3.to_csv(df_financeiro, path=PATHS['gold_financeiro'], dataset=True, mode="overwrite", index=False)
    
    # 6. SALVAMENTO DA MASTER GOLD CONSOLIDADA (O que faltava!)
    wr.s3.to_csv(df_gold, path=PATHS['gold_consolidado'], dataset=True, mode="overwrite", index=False)

    logger.info(f" Workflow v2.0 Finalizado. Gold Master salva em: {PATHS['gold_consolidado']}")

except Exception as e:
    logger.critical(f" FALHA CRÍTICA NO PIPELINE: {str(e)}", exc_info=True)
    raise
