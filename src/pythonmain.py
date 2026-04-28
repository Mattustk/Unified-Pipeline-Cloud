# ==============================================================================
# PROJETO: UNIFIED DATA PIPELINE - GUILHERME GROUP (V2.1)
# DESCRICAO: Framework de ETL para consolidação multi-holding (Tech & Retail).
# REFINAMENTO: Peer-review alinhado com padrões de auditoria financeira.
# ==============================================================================

import pandas as pd
import awswrangler as wr
import logging
import os
from datetime import datetime

# CONFIGURAÇÃO DE LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Unified-Pipeline-Cloud")

# --- ITEM 8: VARIÁVEIS DE AMBIENTE (CONFIGURAÇÃO PROFISSIONAL) ---
BUCKET_BASE = os.getenv("S3_BUCKET_BASE", "s3://guilherme-holding/")
TAXA_COMISSAO = float(os.getenv("TAXA_COMISSAO", 0.01))

# CONTROLE DE EXECUÇÃO
execution_date = datetime.now().strftime("%Y-%m-%d")

# MAPEAMENTO DE AMBIENTE
PATHS = {
    "raw_tech": f"{BUCKET_BASE}nexus-tech/raw/tech_nexus.csv",
    "raw_retail": f"{BUCKET_BASE}nexus-retail/raw/retail_nexus.csv",
    "quarantine": f"{BUCKET_BASE}quarantine/log_erros/",
    "silver_tech": f"{BUCKET_BASE}nexus-tech/silver/",
    "silver_retail": f"{BUCKET_BASE}nexus-retail/silver/",
    "gold_financeiro": f"{BUCKET_BASE}financeiro/gold/",
    "gold_rh": f"{BUCKET_BASE}rh/gold/",
    "gold_consolidado": f"{BUCKET_BASE}guilherme_consolidado/gold/"
}

def validate_data_quality(df, context="PRODUCAO"):
    """
    Função de Quality Gate: Valida integridade financeira, nulos e tipos.
    Retorna apenas registros 100% íntegros.
    """
    df = df.copy()

    # VALIDATION 1: Campos Críticos (ITEM 3: Custo unitário não pode ser nulo agora!)
    campos_obrigatorios = ['id_transacao', 'valor_unitario', 'quantidade', 'valor_total_transacao', 'custo_unitario']
    mask_nulls = df[campos_obrigatorios].isna().any(axis=1)

    # VALIDATION 2: Sanidade de Valores (Negativos ou Zero)
    mask_valores_invalidos = (df['valor_unitario'] <= 0) | (df['quantidade'] <= 0)

    # VALIDATION 3: Integridade de Cálculo
    df['valor_calculado'] = (df['valor_unitario'] * df['quantidade']).round(2)
    mask_erro_calculo = abs(df['valor_calculado'] - df['valor_total_transacao']) > 0.05

    # CONSOLIDAÇÃO DA QUARENTENA
    mask_inconsistente = mask_nulls | mask_valores_invalidos | mask_erro_calculo
    
    df_quarantine = df[mask_inconsistente].copy()
    df_clean = df[~mask_inconsistente].copy()

    # PERSISTÊNCIA DE ERROS (Audit Trail)
    if not df_quarantine.empty:
        logger.warning(f" {context}: {len(df_quarantine)} registros enviados para QUARENTENA.")
        # Adiciona motivo para o analista de dados
        df_quarantine['motivo_rejeicao'] = "Falha de Integridade ou Nulos"
        try:
            wr.s3.to_parquet(
                df_quarantine,
                path=PATHS['quarantine'],
                dataset=True,
                mode="append",
                partition_cols=["motivo_rejeicao"]
            )
        except Exception as e:
            logger.error(f"Erro ao salvar quarentena: {e}")

    return df_clean.drop(columns=['valor_calculado'], errors='ignore')

# WORKFLOW PRINCIPAL
try:
    logger.info(f"--- INICIANDO PIPELINE V2.1 | DATA: {execution_date} ---")

    # 1. CAMADA BRONZE (INGESTÃO)
    df_tech_raw = wr.s3.read_csv(PATHS['raw_tech'], dtype=str)
    df_retail_raw = wr.s3.read_csv(PATHS['raw_retail'], dtype=str)

    # 2. CASTING (Conversão Segura)
    for df in [df_tech_raw, df_retail_raw]:
        df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
        df['valor_total_transacao'] = pd.to_numeric(df['valor_total_transacao'], errors='coerce')
        df['custo_unitario'] = pd.to_numeric(df['custo_unitario'], errors='coerce')
        df['data'] = pd.to_datetime(df['data'], errors='coerce')

    # 3. CAMADA SILVER (QUALITY GATES REAL)
    df_tech_silver = validate_data_quality(df_tech_raw, "NEXUS_TECH")
    df_retail_silver = validate_data_quality(df_retail_raw, "NEXUS_RETAIL")

    # 4. ENGENHARIA DE FEATURES (Particionamento)
    for df in [df_tech_silver, df_retail_silver]:
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month

    # 5. PERSISTÊNCIA SILVER
    for label, df, path in [("TECH", df_tech_silver, PATHS['silver_tech']), 
                             ("RETAIL", df_retail_silver, PATHS['silver_retail'])]:
        wr.s3.to_parquet(df, path=path, dataset=True, mode="overwrite_partitions", partition_cols=["ano", "mes"])
        logger.info(f" Camada Silver {label} atualizada.")

    # 6. CAMADA GOLD (CONSOLIDAÇÃO E BUSINESS LOGIC)
    df_gold = pd.concat([df_tech_silver, df_retail_silver], ignore_index=True)
    
    # Cálculo de métricas profissionais
    df_gold['custo_total'] = df_gold['custo_unitario'] * df_gold['quantidade']
    df_gold['margem_bruta_valor'] = df_gold['valor_total_transacao'] - df_gold['custo_total']

    # 6.1 GOLD RH: Comissionamento
    df_rh = df_gold.groupby(['id_vendedor', 'holding']).agg(
        venda_bruta_total=('valor_total_transacao', 'sum'),
        quantidade_pedidos=('id_transacao', 'count')
    ).reset_index()
    df_rh['comissao_pagar'] = df_rh['venda_bruta_total'] * TAXA_COMISSAO
    df_rh['execution_date'] = execution_date

    # 6.2 GOLD FINANCEIRO: --- ITEM 4: MARGEM BRUTA POR HOLDING ---
    df_financeiro = df_gold.groupby(['holding', 'ano', 'mes']).agg(
        receita_total=('valor_total_transacao', 'sum'),
        custo_total=('custo_total', 'sum'),
        margem_bruta_consolidada=('margem_bruta_valor', 'sum')
    ).reset_index()
    df_financeiro['execution_date'] = execution_date

    # 7. PERSISTÊNCIA GOLD
    wr.s3.to_parquet(df_rh, path=PATHS['gold_rh'], dataset=True, mode="overwrite_partitions", partition_cols=["execution_date"])
    wr.s3.to_parquet(df_financeiro, path=PATHS['gold_financeiro'], dataset=True, mode="overwrite_partitions", partition_cols=["execution_date"])
    wr.s3.to_parquet(df_gold, path=PATHS['gold_consolidado'], dataset=True, mode="overwrite_partitions", partition_cols=["ano", "mes"])

    logger.info(f" PIPELINE FINALIZADO COM SUCESSO | RUN ID: {execution_date}")

except Exception as e:
    logger.critical(f"💥 FALHA CRÍTICA: {str(e)}", exc_info=True)
    raise
