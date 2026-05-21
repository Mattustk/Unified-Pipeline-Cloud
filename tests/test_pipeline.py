import pytest
import pandas as pd
import numpy as np
# Correção de importação do pacote real de produção
from src.pythonmain import validate_data_quality, apply_type_casting

@pytest.fixture
def base_data_mock():
    """Cria dados simulados simulando a Camada Bronze (String-Only)"""
    return pd.DataFrame({
        'id_transacao': ['TRX-OK', 'TRX-NULL', 'TRX-NEG', 'TRX-MATH'],
        'valor_unitario': ['100.0', '50.0', '-10.0', '20.0'],
        'quantidade': ['2', '2', '5', '3'],
        'custo_unitario': ['40.0', None, '10.0', '5.0'],
        'valor_total_transacao': ['200.0', '100.0', '-50.0', '90.0'] # TRX-MATH: 20*3=60, total informado=90
    })

def test_pipeline_end_to_end_quality_gate(base_data_mock):
    # 1. Executa o casting real de produção
    df_casted = apply_type_casting(base_data_mock)
    
    # 2. Executa o gate de qualidade
    df_clean, df_quarantine = validate_data_quality(df_casted, "AMB_TESTE")
    
    # VALIDAÇÃO DE SUCESSO
    assert len(df_clean) == 1
    assert df_clean.iloc[0]['id_transacao'] == 'TRX-OK'
    
    # VALIDAÇÃO DE QUARENTENA GRANULAR (O que o Conselho exigiu)
    assert len(df_quarantine) == 3
    
    # Verifica classificação de erro por motivo específico
    motivos = df_quarantine.set_index('id_transacao')['motivo_rejeicao'].to_dict()
    assert motivos['TRX-NULL'] == 'CAMPOS_OBRIGATORIOS_NULOS'
    assert motivos['TRX-NEG'] == 'VALORES_MONETARIOS_NEGATIVOS'
    assert motivos['TRX-MATH'] == 'DIVERGENCIA_MATEMATICA_PRECO_QTD'

def test_edge_case_math_tolerance():
    """Testa os limites de borda da validação de ponto flutuante (Delta de 0.05)"""
    df_edge = pd.DataFrame({
        'id_transacao': ['TRX-LIMIT-OK', 'TRX-LIMIT-FAIL'],
        'valor_unitario': [10.0, 10.0],
        'quantidade': [3, 3],
        'custo_unitario': [2.0, 2.0],
        'valor_total_transacao': [30.05, 30.06] # 0.05 passa, 0.06 roda
    })
    
    df_clean, df_quarantine = validate_data_quality(df_edge, "TEST_EDGE")
    assert 'TRX-LIMIT-OK' in df_clean['id_transacao'].values
    assert 'TRX-LIMIT-FAIL' in df_quarantine['id_transacao'].values
