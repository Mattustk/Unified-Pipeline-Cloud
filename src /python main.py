
# ==============================================================================
# PROJETO: UNIFIED DATA PIPELINE - GUILHERME GROUP (V2.0)
# DESCRICAO: Framework de ETL para consolidação multi-holding (Tech & Retail).
# ARQUITETURA: Medallion (Raw -> Silver -> Gold) com Quality Gates integrados.
# TECNOLOGIAS: Python, Pandas, AWS Wrangler, Boto3.
# ==============================================================================

import pandas as pd
import awswrangler as wr
import logging
from datetime import datetime

# CONFIGURAÇÃO DE LOGGING: Monitoramento estruturado para auditoria
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MirantePipeline")

# CONTROLE DE EXECUÇÃO: Data de processamento para rastreabilidade (Run ID)
execution_date = datetime.now().strftime("%Y-%m-%d")

# MAPEAMENTO DE AMBIENTE: Estrutura de camadas no S3 (Data Lake)
BUCKET_BASE = "s3://guilherme-holding/"
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

# REGRAS DE NEGÓCIO
TAXA_COMISSAO = 0.01

def validate_data_quality(df, context):
    """
    Função de Quality Gate: Valida integridade financeira, nulos e tipos.
    Separa o dataset entre registros 'Clean' e 'Quarantine'.
    """
    df = df.copy()

    # VALIDATION 1: Integridade Financeira (Cálculo Unitário x Qtd vs Total)
    # Aplicamos round(2) para evitar erros de precisão de ponto flutuante do Python
    df['valor_calculado'] = (df['valor_unitario'] * df['quantidade']).round(2)
    df['check_total'] = abs(df['valor_calculado'] - df['valor_total_transacao'])

    # Máscara de erro financeiro: Tolerância máxima de 0.05 (5 centavos)
    mask_check_financeiro = df['check_total'] > 0.05

    # VALIDATION 2: Presença de Campos Críticos (Não permite nulos em chaves e valores)
    # axis=1 valida a linha inteira; se houver um nulo em qualquer coluna citada, a linha é marcada.
    mask_nulls = df[
        ['id_transacao', 'valor_unitario', 'quantidade', 'valor_total_transacao']
    ].isna().any(axis=1)

    # VALIDATION 3: Regras de Sanidade (Valores totais não podem ser zero ou negativos)
    mask_negativos = df['valor_total_transacao'] <= 0

    # CONSOLIDAÇÃO: Agrupa todas as inconsistências em um único filtro
    mask_inconsistente = mask_nulls | mask_negativos | mask_check_financeiro

    # SEGREGAÇÃO: Separa dados inconsistentes para auditoria (Quarentena)
    df_quarantine = df[mask_inconsistente].copy()
    df_quarantine['motivo_rejeicao'] = "Erro financeiro, nulos ou valores inválidos"

    # LIMPEZA: Remove colunas auxiliares de validação antes de avançar para Silver
    df_clean = df[~mask_inconsistente].drop(columns=['check_total', 'valor_calculado'])

    # PERSISTÊNCIA DE ERROS: Salva registros inválidos no S3 particionados por erro
    if not df_quarantine.empty:
        logger.warning(f" {context}: {len(df_quarantine)} registros enviados para QUARENTENA.")
        wr.s3.to_parquet(
            df_quarantine,
            path=PATHS['quarantine'],
            dataset=True,
            mode="append",
            partition_cols=["motivo_rejeicao"]
        )

    return df_clean

# WORKFLOW PRINCIPAL
try:
    logger.info("--- INICIANDO PIPELINE DE CONSOLIDAÇÃO V3.0 ---")

    # 1. CAMADA BRONZE (INGESTÃO): Leitura como String para evitar perdas de schema
    df_tech_raw = wr.s3.read_csv(PATHS['raw_tech'], dtype=str).copy()
    df_retail_raw = wr.s3.read_csv(PATHS['raw_retail'], dtype=str).copy()

    # 2. CASTING: Conversão de tipos para operações matemáticas e temporais
    for df in [df_tech_raw, df_retail_raw]:
        df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
        df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
        df['valor_total_transacao'] = pd.to_numeric(df['valor_total_transacao'], errors='coerce')
        df['custo_unitario'] = pd.to_numeric(df['custo_unitario'], errors='coerce')
        df['data'] = pd.to_datetime(df['data'], errors='coerce')

    # 3. CAMADA SILVER (PROCESSAMENTO): Aplicação dos Quality Gates
    df_tech_silver = validate_data_quality(df_tech_raw, "NEXUS_TECH")
    df_retail_silver = validate_data_quality(df_retail_raw, "NEXUS_RETAIL")

    # 4. ENGENHARIA DE FEATURES: Criação de chaves de particionamento (Ano/Mês)
    for df in [df_tech_silver, df_retail_silver]:
        df['ano'] = df['data'].dt.year
        df['mes'] = df['data'].dt.month

    # 5. PERSISTÊNCIA SILVER: Escrita em Parquet Particionado no S3
    wr.s3.to_parquet(
        df_tech_silver,
        path=PATHS['silver_tech'],
        dataset=True,
        mode="overwrite_partitions",
        partition_cols=["ano", "mes"]
    )

    wr.s3.to_parquet(
        df_retail_silver,
        path=PATHS['silver_retail'],
        dataset=True,
        mode="overwrite_partitions",
        partition_cols=["ano", "mes"]
    )

    # 6. CAMADA GOLD: Consolidação de Holdings e Agregações de Negócio
    df_gold = pd.concat([df_tech_silver, df_retail_silver], ignore_index=True)
    
    df_gold['custo_unitario'] = df_gold['custo_unitario'].fillna(0) # Evita que vendas fiquem sem custo na análise


    # Cálculo do custo total (Business Logic: Custo Unitário * Quantidade)
    df_gold['custo_total'] = df_gold['custo_unitario'] * df_gold['quantidade']

    # 6.1 GOLD RH: Performance de vendas e comissionamento por vendedor
    df_rh = df_gold.groupby(['id_vendedor', 'holding']).agg(
        venda_bruta=('valor_total_transacao', 'sum'),
        total_vendas=('id_transacao', 'count')
    ).reset_index()

    df_rh['comissao_valor'] = df_rh['venda_bruta'] * TAXA_COMISSAO
    df_rh['execution_date'] = execution_date

    # 6.2 GOLD FINANCEIRO: Visão de Receita vs Custo Operacional
    df_financeiro = df_gold.groupby(['data', 'holding']).agg(
        receita=('valor_total_transacao', 'sum'),
        custo=('custo_total', 'sum')
    ).reset_index()

    df_financeiro['execution_date'] = execution_date

    # 7. PERSISTÊNCIA GOLD: Escrita final com governança e auditoria
    wr.s3.to_parquet(
        df_rh,
        path=PATHS['gold_rh'],
        dataset=True,
        mode="overwrite_partitions",
        partition_cols=["execution_date"]
    )

    wr.s3.to_parquet(
        df_financeiro,
        path=PATHS['gold_financeiro'],
        dataset=True,
        mode="overwrite_partitions",
        partition_cols=["execution_date"]
    )

    # Consolidado Geral para Data Discovery
    wr.s3.to_parquet(
        df_gold,
        path=PATHS['gold_consolidado'],
        dataset=True,
        mode="overwrite_partitions",
        partition_cols=["ano", "mes"]
    )

    logger.info(f" Workflow Finalizado com Sucesso | Run: {execution_date}")

except Exception as e:
    # TRATAMENTO DE ERROS: Captura falhas críticas e gera log detalhado (Stack Trace)
    logger.critical(f" FALHA CRÍTICA NO PIPELINE: {str(e)}", exc_info=True)
    raise
