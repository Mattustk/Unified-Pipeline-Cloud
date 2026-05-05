# ==============================================================================
# PROJETO: UNIFIED DATA PIPELINE - GUILHERME GROUP
# Este script automatiza a coleta, limpeza e organização de dados na nuvem (AWS).
# ==============================================================================

import pandas as pd              # Biblioteca para manipulação de tabelas (DataFrames)
import awswrangler as wr         # Conector de elite para serviços AWS (S3, Glue, Athena)
import logging                   # Sistema para registrar o status de execução (logs)
import os                        # Para interagir com o sistema e variáveis de ambiente
from datetime import datetime    # Para capturar e formatar a data atual da execução

# --- CONFIGURAÇÃO DE COMUNICAÇÃO ---
# Define que o script vai "falar" no console o que está fazendo em tempo real
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Unified-Pipeline-Cloud")

# --- ITEM 8: CONFIGURAÇÕES EXTERNAS (BOAS PRÁTICAS) ---
# Busca o endereço do servidor (Bucket S3) e a taxa de comissão de fora do código
BUCKET_BASE = os.getenv("S3_BUCKET_BASE", "s3://guilherme-holding/")
TAXA_COMISSAO = float(os.getenv("TAXA_COMISSAO", 0.01)) # 1% por padrão

# Define a data da execução do pipeline para organizar os arquivos depois
execution_date = datetime.now().strftime("%Y-%m-%d")

# --- MAPEAMENTO DE DIRETÓRIOS (ONDE O DADO MORA) ---
PATHS = {
    "raw_tech": f"{BUCKET_BASE}nexus-tech/raw/tech_nexus.csv",      # Dado bruto Tech
    "raw_retail": f"{BUCKET_BASE}nexus-retail/raw/retail_nexus.csv", # Dado bruto Varejo
    "quarantine": f"{BUCKET_BASE}quarantine/log_erros/",            # Pasta de erros
    "silver_tech": f"{BUCKET_BASE}nexus-tech/silver/",              # Dado limpo Tech
    "silver_retail": f"{BUCKET_BASE}nexus-retail/silver/",          # Dado limpo Varejo
    "gold_financeiro": f"{BUCKET_BASE}financeiro/gold/",            # Relatório Financeiro final
    "gold_rh": f"{BUCKET_BASE}rh/gold/",                            # Relatório de Comissões final
    "gold_consolidado": f"{BUCKET_BASE}guilherme_consolidado/gold/" # Base toda unificada
}

def validate_data_quality(df, context="PRODUCAO"):
    """
    QUALITY GATE: Função que filtra registros ruins antes de salvar.
    """
    df = df.copy() # Cria uma cópia para não alterar o dado original por acidente

    # VALIDAÇÃO 1: Verifica se existem campos vazios em colunas obrigatórias
    campos_obrigatorios = ['id_transacao', 'valor_unitario', 'quantidade', 'valor_total_transacao', 'custo_unitario']
    mask_nulls = df[campos_obrigatorios].isna().any(axis=1)

    # VALIDAÇÃO 2: Bloqueia valores impossíveis (venda negativa ou zero)
    mask_valores_invalidos = (df['valor_unitario'] <= 0) | (df['quantidade'] <= 0)

    # VALIDAÇÃO 3: Checagem de Cálculo (O total bate com Preço x Quantidade?)
    df['valor_calculado'] = (df['valor_unitario'] * df['quantidade']).round(2)
    mask_erro_calculo = abs(df['valor_calculado'] - df['valor_total_transacao']) > 0.05

    # UNIFICAÇÃO DAS FALHAS: Se falhar em qualquer um dos 3, vai para a quarentena
    mask_inconsistente = mask_nulls | mask_valores_invalidos | mask_erro_calculo
    
    df_quarantine = df[mask_inconsistente].copy() # Tabela de erros
    df_clean = df[~mask_inconsistente].copy()    # Tabela de acertos (limpa)

    # AUDITORIA: Salva os erros no S3 para análise posterior
    if not df_quarantine.empty:
        logger.warning(f" {context}: {len(df_quarantine)} registros enviados para QUARENTENA.")
        df_quarantine['motivo_rejeicao'] = "Falha de Integridade ou Nulos"
        
        # Só salva no S3 se não for um teste automático (CI/CD)
        if os.getenv("GITHUB_ACTIONS") != "true":
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

    # Retorna apenas o que presta para o pipeline continuar
    return df_clean.drop(columns=['valor_calculado'], errors='ignore')

# --- BLOCO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    try:
        logger.info(f"--- INICIANDO PIPELINE V2.2 | DATA: {execution_date} ---")

        # 1. CAMADA BRONZE (INGESTÃO)
        # Lê os arquivos CSV brutos da nuvem. Lemos tudo como 'str' (texto) para evitar erros iniciais.
        df_tech_raw = wr.s3.read_csv(PATHS['raw_tech'], dtype=str)
        df_retail_raw = wr.s3.read_csv(PATHS['raw_retail'], dtype=str)

        # 2. CASTING (TIPAGEM)
        # Converte as colunas de texto para Números e Datas reais
        for df in [df_tech_raw, df_retail_raw]:
            df['valor_unitario'] = pd.to_numeric(df['valor_unitario'], errors='coerce')
            df['quantidade'] = pd.to_numeric(df['quantidade'], errors='coerce')
            df['valor_total_transacao'] = pd.to_numeric(df['valor_total_transacao'], errors='coerce')
            df['custo_unitario'] = pd.to_numeric(df['custo_unitario'], errors='coerce')
            df['data'] = pd.to_datetime(df['data'], errors='coerce')

        # 3. CAMADA SILVER (PROCESSAMENTO E LIMPEZA)
        # Passa os dados brutos pelo "Segurança" (Quality Gate)
        df_tech_silver = validate_data_quality(df_tech_raw, "NEXUS_TECH")
        df_retail_silver = validate_data_quality(df_retail_raw, "NEXUS_RETAIL")

        # 4. ENGENHARIA DE FEATURES
        # Extrai Ano e Mês para facilitar relatórios e organização de pastas
        for df in [df_tech_silver, df_retail_silver]:
            df['ano'] = df['data'].dt.year
            df['mes'] = df['data'].dt.month

        # 5. PERSISTÊNCIA SILVER
        # Salva em PARQUET (formato de alta performance) particionado por Ano/Mês
        for label, df, path in [("TECH", df_tech_silver, PATHS['silver_tech']), 
                                 ("RETAIL", df_retail_silver, PATHS['silver_retail'])]:
            wr.s3.to_parquet(df, path=path, dataset=True, mode="overwrite_partitions", partition_cols=["ano", "mes"])
            logger.info(f" Camada Silver {label} atualizada.")

        # 6. CAMADA GOLD (UNIFICAÇÃO E REGRAS DE NEGÓCIO)
        # Junta Tech e Retail em uma única base de dados consolidada
        df_gold = pd.concat([df_tech_silver, df_retail_silver], ignore_index=True)
        
        # Cria métricas de lucro
        df_gold['custo_total'] = df_gold['custo_unitario'] * df_gold['quantidade']
        df_gold['margem_bruta_valor'] = df_gold['valor_total_transacao'] - df_gold['custo_total']

        # 6.1 GOLD RH (Cálculo de Comissões)
        # Agrupa por vendedor para saber quanto ele vendeu e quanto deve ganhar
        df_rh = df_gold.groupby(['id_vendedor', 'holding']).agg(
            venda_bruta_total=('valor_total_transacao', 'sum'),
            quantidade_pedidos=('id_transacao', 'count')
        ).reset_index()
        df_rh['comissao_pagar'] = df_rh['venda_bruta_total'] * TAXA_COMISSAO
        df_rh['execution_date'] = execution_date

        # 6.2 GOLD FINANCEIRO (Visão de Diretoria)
        # Agrupa por Holding e Mês para ver a saúde financeira da empresa
        df_financeiro = df_gold.groupby(['holding', 'ano', 'mes']).agg(
            receita_total=('valor_total_transacao', 'sum'),
            custo_total=('custo_total', 'sum'),
            margem_bruta_consolidada=('margem_bruta_valor', 'sum')
        ).reset_index()
        df_financeiro['execution_date'] = execution_date

        # 7. SALVAMENTO FINAL (PRONTO PARA DASHBOARDS)
        # Salva os resultados finais que serão lidos pelo Power BI / Athena
        wr.s3.to_parquet(df_rh, path=PATHS['gold_rh'], dataset=True, mode="overwrite_partitions", partition_cols=["execution_date"])
        wr.s3.to_parquet(df_financeiro, path=PATHS['gold_financeiro'], dataset=True, mode="overwrite_partitions", partition_cols=["execution_date"])
        wr.s3.to_parquet(df_gold, path=PATHS['gold_consolidado'], dataset=True, mode="overwrite_partitions", partition_cols=["ano", "mes"])

        logger.info(f"🚀 PIPELINE FINALIZADO COM SUCESSO | RUN ID: {execution_date}")

    except Exception as e:
        # Se qualquer coisa travar, este bloco captura o erro e avisa no log
        logger.critical(f" FALHA CRÍTICA NO PIPELINE: {str(e)}", exc_info=True)
        raise # Interrompe o processo para evitar salvar dados errados
