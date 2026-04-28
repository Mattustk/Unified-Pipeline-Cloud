
# ==============================================================================
# PROJETO: UNIFIED DATA PIPELINE - GUILHERME GROUP (V2.0)
# DESCRICAO: Framework de ETL para consolidação multi-holding (Tech & Retail).
# ARQUITETURA: Medallion (Raw -> Silver -> Gold) com Quality Gates integrados.
# TECNOLOGIAS: Python, Pandas, AWS Wrangler, Boto3, Pytest.
# ==============================================================================

import pandas as pd
import awswrangler as wr
import boto3
import logging
from datetime import datetime

# 1. OBSERVABILIDADE: Configuração de log estruturado para monitoramento em produção
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataEngineering_Mirante")

# Configurações de Path (S3 Data Lake)
BUCKET_BASE = "___________"
PATHS = {
    "raw_tech": f"{BUCKET_BASE}___________",
    "raw_retail": f"{BUCKET_BASE}___________",
    "quarantine": f"{BUCKET_BASE}___________",
    "silver_tech": f"{BUCKET_BASE}___________",
    "silver_retail": f"{BUCKET_BASE}___________",
    "gold_financeiro": f"{BUCKET_BASE}___________",
    "gold_rh": f"{BUCKET_BASE}___________",
    "gold_consolidado": f"{BUCKET_BASE}___________" 
}

# 2. GOVERNANÇA FINANCEIRA: ADR (Architectural Decision Record) para taxas de comissão
TAXA_COMISSAO = 0.01  # Definição de constante para cálculo de provisões de RH

def validate_data_quality(df, context):
    """
    Implementa Data Quality Gates (DQ). 
    Aplica filtros de integridade e desvia registros inconsistentes para Quarentena.
    Retorna: (df_clean, df_quarantine)
    """
    
    # Check 1: Integridade de Cálculo (Drift Financeiro)
    # Valida se o delta entre (P x Q) e o Total reportado é superior à margem de tolerância (0.01)
    df['check_total'] = abs((df['valor_unitario'] * df['quantidade']) - df['valor_total_transacao'])
    mask_check_financeiro = df['check_total'] > 0.01 
    
    # Check 2: Validação de Constraints (Nulos e Negativos)
    # Filtro para garantir que IDs essenciais existam e valores transacionais sejam positivos
    mask_inconsistente = (
        df['id_transacao'].isna() | 
        (df['valor_total_transacao'] <= 0) |  
        mask_check_financeiro
    )
    
    # Isolamento de Dados Inconsistentes (Quarentena)
    df_quarantine = df[mask_inconsistente].copy()
    df_quarantine['motivo_rejeicao'] = "Inconsistência Financeira ou Falha de Schema/ID"
    
    # Dataset Higienizado
    df_clean = df[~mask_inconsistente].drop(columns=['check_total']) 
    
    # Persistência de Erros para Auditoria Posterior no S3
    if not df_quarantine.empty:
        logger.warning(f"DQ Alert [{context}]: {len(df_quarantine)} registros desviados para QUARENTENA.")
        wr.s3.to_csv(df_quarantine, path=PATHS['quarantine'], dataset=True, mode="append", index=False)
        
    return df_clean

try:
    logger.info("--- START WORKFLOW V2.0: ARQUITETURA CLOUD NATIVA ---") 

    # 3. INGESTÃO BRONZE: Schema Enforcement & Tipo Abstrato (String)
    # Mantemos os tipos como String na leitura inicial para evitar truncagem ou erro de cast prematuro
    df_tech_raw = wr.s3.read_csv(path=PATHS['raw_tech'], dtype=str)
    df_retail_raw = wr.s3.read_csv(path=PATHS['raw_retail'], dtype=str)

    # Casting Controlado: Conversão explícita para tipos numéricos e temporais
    for df in [df_tech_raw, df_retail_raw]:
        df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
        df['valor_total_transacao'] = pd.to_numeric(df['valor_total_transacao'], errors='coerce')
        df['custo_unitario'] = pd.to_numeric(df['custo_unitario'], errors='coerce')
        df['data'] = pd.to_datetime(df['data'], errors='coerce')

    # 4. SILVER LAYER: Processamento de Higienização e DQ Gates
    df_tech_silver = validate_data_quality(df_tech_raw, "NEXUS_TECH")
    df_retail_silver = validate_data_quality(df_retail_raw, "NEXUS_RETAIL")

    # Persistência em Parquet: Otimização de storage e performance analítica
    wr.s3.to_parquet(df_tech_silver, path=PATHS['silver_tech'], dataset=True, mode="overwrite")
    wr.s3.to_parquet(df_retail_silver, path=PATHS['silver_retail'], dataset=True, mode="overwrite")

    # 5. GOLD LAYER: Consolidação e Business Intelligence (Consolidação Multi-Holding)
    df_gold = pd.concat([df_tech_silver, df_retail_silver], ignore_index=True)
    
    # Agregação Gold RH: Cálculo de performance de vendas e comissionamento
    df_rh = df_gold.groupby(['id_vendedor', 'holding']).agg({
        'valor_total_transacao': 'sum', 'id_transacao': 'count'
    }).rename(columns={'id_transacao': 'total_vendas', 'valor_total_transacao': 'venda_bruta'}).reset_index()
    df_rh['comissao_valor'] = df_rh['venda_bruta'] * TAXA_COMISSAO

    # Agregação Gold Financeiro: Visão temporal de faturamento e custos
    df_financeiro = df_gold.groupby(['data', 'holding']).agg({
        'valor_total_transacao': 'sum', 'custo_unitario': 'sum'
    }).reset_index()

    # Publicação de Datasets Finais
    wr.s3.to_csv(df_rh, path=PATHS['gold_rh'], dataset=True, mode="overwrite", index=False)
    wr.s3.to_csv(df_financeiro, path=PATHS['gold_financeiro'], dataset=True, mode="overwrite", index=False)
    
    # Exportação da Master Gold Consolidada (Fonte Única da Verdade)
    wr.s3.to_csv(df_gold, path=PATHS['gold_consolidado'], dataset=True, mode="overwrite", index=False)

    logger.info(f"Workflow Finalizado. Artefatos de dados publicados em: {PATHS['gold_consolidado']}") 

except Exception as e:
    # Tratamento de exceções e log de stack trace para Debugging
    logger.critical(f"FATAL ERROR: Falha na execução do pipeline. Causa: {str(e)}", exc_info=True)
    raise
