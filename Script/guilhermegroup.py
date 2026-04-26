
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

# ==========================================
# CONFIGURAÇÃO DOS CAMINHOS DE ORIGEM E DESTINO (S3)
# ==========================================
BUCKET_RAW_TECH = "s3://guilherme-holding/nexus-tech/raw/tech_nexus.csv"
BUCKET_RAW_RETAIL = "s3://guilherme-holding/nexus-retail/raw/retail_nexus.csv"

BUCKET_OUT_TECH = "s3://guilherme-holding/nexus-tech/processed/"
BUCKET_OUT_RETAIL = "s3://guilherme-holding/nexus-retail/processed/"
BUCKET_OUT_FINAL = "s3://guilherme-holding/guilherme_consolidado/gold_zone/"

BUCKET_GOLD_DIRETORIA = "s3://guilherme-holding/Diretoria/gold/"
BUCKET_GOLD_RH = "s3://guilherme-holding/rh/gold/"
BUCKET_GOLD_FINANCEIRO = "s3://guilherme-holding/financeiro/gold/"

try:
    # ---------------------------------------------------------
    # 1. CARGA DOS DADOS (INGESTÃO)
    # ---------------------------------------------------------
    df_tech = wr.s3.read_csv(path=BUCKET_RAW_TECH)
    df_retail = wr.s3.read_csv(path=BUCKET_RAW_RETAIL)

    # ---------------------------------------------------------
    # 2. LIMPEZA E VALIDAÇÃO: DF_TECH
    # ---------------------------------------------------------
    # Conversão de tipos para garantir consistência nos cálculos
    df_tech['data'] = pd.to_datetime(df_tech['data'])
    df_tech['quantidade'] = pd.to_numeric(df_tech['quantidade'])
    df_tech['valor_unitario'] = pd.to_numeric(df_tech['valor_unitario'])
    df_tech['custo_unitario'] = pd.to_numeric(df_tech['custo_unitario'])
    df_tech['valor_total_transacao'] = pd.to_numeric(df_tech['valor_total_transacao'])
    
    # Sanitização: Remove caracteres especiais de CPFs
    df_tech['cpf_cliente'] = df_tech['cpf_cliente'].astype(str).str.replace(r'\D', '', regex=True)

    # Remoção de registros inválidos e duplicidade de transação
    df_tech = df_tech.dropna(subset=['id_transacao', 'valor_total_transacao'])
    df_tech = df_tech.drop_duplicates(subset=['id_transacao'])
 
    # --- VALIDAÇÃO CRÍTICA: DF_TECH (Data Quality) ---
    assert df_tech['id_transacao'].isna().sum() == 0, "Tech: ID de transação nulo"
    assert df_tech['id_vendedor'].isna().sum() == 0, "Tech: Venda sem identificação de vendedor"
    assert (df_tech['valor_total_transacao'] > 0).all(), "Tech: Venda com valor zero ou negativo"
    assert (df_tech['custo_unitario'] >= 0).all(), "Tech: Custo negativo detectado"
    
    # Valida se a multiplicação Unitário x Qtd bate com o Total informado
    check_tech = (df_tech['valor_unitario'] * df_tech['quantidade']) - df_tech['valor_total_transacao']
    assert (check_tech.abs() < 0.1).all(), "Tech: Divergência entre Unitário x Qtd e Valor Total"
    
    # ---------------------------------------------------------
    # 3. LIMPEZA E VALIDAÇÃO: DF_RETAIL
    # ---------------------------------------------------------
    df_retail['data'] = pd.to_datetime(df_retail['data'])
    df_retail['quantidade'] = pd.to_numeric(df_retail['quantidade'])
    df_retail['valor_unitario'] = pd.to_numeric(df_retail['valor_unitario'])
    df_retail['custo_unitario'] = pd.to_numeric(df_retail['custo_unitario'])
    df_retail['valor_total_transacao'] = pd.to_numeric(df_retail['valor_total_transacao'])
    df_retail['cpf_cliente'] = df_retail['cpf_cliente'].astype(str).str.replace(r'\D', '', regex=True)

    df_retail = df_retail.dropna(subset=['id_transacao', 'valor_total_transacao'])
    df_retail = df_retail.drop_duplicates(subset=['id_transacao'])

    # --- VALIDAÇÃO CRÍTICA: DF_RETAIL (Data Quality) ---
    assert df_retail['valor_total_transacao'].isna().sum() == 0, "Retail: ID de venda nulo"
    assert df_retail['id_vendedor'].isna().sum() == 0, "Retail: Venda sem identificação de vendedor"
    assert (df_retail['valor_total_transacao'] > 0).all(), "Retail: Venda com valor zero ou negativo"
    assert (df_retail['custo_unitario'] >= 0).all(), "Retail: Custo negativo detectado"
    
    check_retail = (df_retail['valor_unitario'] * df_retail['quantidade']) - df_retail['valor_total_transacao']
    assert (check_retail.abs() < 0.1).all(), "Retail: Divergência entre Unitário x Qtd e Valor Total"
    
    # ---------------------------------------------------------
    # 4. UNIFICAÇÃO DAS BASES (HOLDING CONSOLIDADA)
    # ---------------------------------------------------------
    df_tech_ready = df_tech.copy() 
    df_final = pd.concat([df_tech_ready, df_retail], ignore_index=True)
    
    # ---------------------------------------------------------
    # 5. AGREGAÇÕES PARA ÁREAS DE NEGÓCIO (GOLD TABLES)
    # ---------------------------------------------------------
    
    # FINANCEIRO: Visão de Receita Diária e Volume
    df_financeiro = df_final.groupby(['data', 'holding']).agg({
        'valor_total_transacao': 'sum',
        'custo_unitario': 'sum', 
        'id_transacao': 'count'
    }).rename(columns={'id_transacao': 'qtd_transacoes', 'valor_total_transacao': 'receita_bruta'}).reset_index()
    
    # RH: Desempenho do Vendedor e Cálculo de Comissão (5%)
    df_rh = df_final.groupby(['id_vendedor', 'holding']).agg({
        'valor_total_transacao': 'sum',
        'id_transacao': 'count'
    }).rename(columns={'id_transacao': 'total_vendas', 'valor_total_transacao': 'valor_acumulado'}).reset_index() 
    
    df_rh['comissao_a_pagar'] = df_rh['valor_acumulado'] * 0.05
    
    # DIRETORIA / MARKETING: Ranking de itens mais vendidos por unidade
    df_marketing = df_final.groupby(['holding', 'item_vendido']).agg({
        'quantidade': 'sum',
        'valor_total_transacao': 'sum'
    }).sort_values(by='quantidade', ascending=False).reset_index()

    # ---------------------------------------------------------
    # 6. SALVAMENTO  NO S3 (FORMATO PARQUET)
    # ---------------------------------------------------------
    wr.s3.to_parquet(df=df_tech, path=BUCKET_OUT_TECH, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_retail, path=BUCKET_OUT_RETAIL, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_final, path=BUCKET_OUT_FINAL, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_marketing, path=BUCKET_GOLD_DIRETORIA, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_rh, path=BUCKET_GOLD_RH, dataset=True, mode="overwrite")
    wr.s3.to_parquet(df=df_financeiro, path=BUCKET_GOLD_FINANCEIRO, dataset=True, mode="overwrite")

    # ---------------------------------------------------------
    # 7. SALVAMENTO FINAL NO S3 (FORMATO CSV para Excel ou Google Sheets)
    # ---------------------------------------------------------
    wr.s3.to_csv(df=df_rh, 
                 path="s3://guilherme-holding/rh/export_excel/", 
                 index=False, 
                 dataset=True, # <
                 mode="overwrite")
    
    wr.s3.to_csv(df=df_marketing, 
                 path="s3://guilherme-holding/Diretoria/export_excel/", 
                 index=False, 
                 dataset=True, 
                 mode="overwrite")
    
    wr.s3.to_csv(df=df_financeiro, 
                 path="s3://guilherme-holding/financeiro/export_excel/", 
                 index=False, 
                 dataset=True, 
                 mode="overwrite")


except Exception as e:
    # Captura qualquer erro no processo e exibe no log
    print(f" ERRO: {e}")
else:
    # Confirmação de sucesso do pipeline
    print(f" WORKFLOW CONCLUÍDO!")
