import pytest
import pandas as pd
import numpy as np
# Importa a função REAL do seu arquivo de produção
from src.pythonmain import validate_data_quality

@pytest.fixture
def data_mock():
    """Cria um DataFrame de teste com casos reais de erro"""
    return pd.DataFrame({
        'id_transacao': ['TRX-001', 'TRX-002', 'TRX-003', 'TRX-004'],
        'valor_unitario': [100.0, -10.0, 50.0, 200.0],       # Erro no 2 (Negativo)
        'quantidade': [2, 1, 3, 2],
        'custo_unitario': [50.0, 5.0, None, 100.0],         # Erro no 3 (Custo Nulo)
        'valor_total_transacao': [200.0, -10.0, 150.0, 500.0] # Erro no 4 (Cálculo errado: 200*2 != 500)
    })

def test_quality_gate_filters_negatives(data_mock):
    """Garante que valores negativos caiam na quarentena"""
    df_clean = validate_data_quality(data_mock, "TEST_NEGATIVOS")
    
    # O TRX-002 deve ter sido removido por ser negativo
    assert 'TRX-002' not in df_clean['id_transacao'].values

def test_quality_gate_filters_null_costs(data_mock):
    """Garante que custos nulos não passem para a camada Gold"""
    df_clean = validate_data_quality(data_mock, "TEST_NULOS")
    
    # O TRX-003 deve ter sido removido (Custo None)
    assert 'TRX-003' not in df_clean['id_transacao'].values
    assert df_clean['custo_unitario'].isnull().sum() == 0

def test_quality_gate_validates_math_integrity(data_mock):
    """Garante que erros de cálculo (Unit x Qtd != Total) sejam interceptados"""
    df_clean = validate_data_quality(data_mock, "TEST_MATEMATICA")
    
    # O TRX-004 (200 * 2 = 400, mas o total era 500) deve ser barrado
    assert 'TRX-004' not in df_clean['id_transacao'].values

def test_quality_gate_final_count(data_mock):
    """Garante que apenas o dado 100% correto (TRX-001) sobreviva"""
    df_clean = validate_data_quality(data_mock, "TEST_FINAL")
    
    # Apenas 1 registro deve ser aprovado
    assert len(df_clean) == 1
    assert df_clean.iloc[0]['id_transacao'] == 'TRX-001'
