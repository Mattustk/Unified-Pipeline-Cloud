import pandas as pd
import pytest

# Simula a lógica de validação que você tem no seu script principal
def validar_dados(df):
    # Regra: Preço * Quantidade deve ser igual ao Total
    mask_check_total = (df['valor_unitario'] * df['quantidade'] == df['valor_total_transacao'])
    # Regra: Não aceita valores negativos
    mask_no_negatives = (df['valor_unitario'] > 0) & (df['quantidade'] > 0)
    
    df_valido = df[mask_check_total & mask_no_negatives]
    df_invalido = df[~(mask_check_total & mask_no_negatives)]
    return df_valido, df_invalido

def test_quality_gate_calculo_correto():
    """Testa se dados corretos passam pelo filtro"""
    data = {
        'id_transacao': ['T1'],
        'valor_unitario': [100.0],
        'quantidade': [2],
        'valor_total_transacao': [200.0]
    }
    df = pd.DataFrame(data)
    validos, invalidos = validar_dados(df)
    
    assert len(validos) == 1
    assert len(invalidos) == 0

def test_quality_gate_calculo_errado():
    """Testa se dados com erro de conta vão para a quarentena"""
    data = {
        'id_transacao': ['T2'],
        'valor_unitario': [100.0],
        'quantidade': [2],
        'valor_total_transacao': [999.0] # Erro proposital
    }
    df = pd.DataFrame(data)
    validos, invalidos = validar_dados(df)
    
    assert len(validos) == 0
    assert len(invalidos) == 1

def test_valores_negativos():
    """Testa se valores negativos são rejeitados"""
    data = {
        'id_transacao': ['T3'],
        'valor_unitario': [-50.0],
        'quantidade': [1],
        'valor_total_transacao': [-50.0]
    }
    df = pd.DataFrame(data)
    validos, invalidos = validar_dados(df)
    
    assert len(validos) == 0
    assert len(invalidos) == 1
    